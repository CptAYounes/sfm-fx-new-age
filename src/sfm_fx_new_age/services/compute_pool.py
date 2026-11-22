"""Demand-grown CPU-only process pool; owner retains all application authority."""
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path
from threading import get_ident
import os,math
from typing import Callable,Any


def worker_limit(affinity:int,*,quota:float|None=None,memory_bytes:int|None=None,requested:str|int='auto')->int:
    if requested!='auto' and (type(requested) is not int or requested<1):raise ValueError('compute workers must be auto or a positive integer')
    effective=max(1,min(affinity,math.ceil(quota) if quota is not None else affinity))
    # Reserve one scheduling slot for the Qt/core/SDK owners. This is a ceiling,
    # not a request to keep every core busy; idle processes consume no CPU work.
    ceiling=max(1,effective-1)
    if memory_bytes is not None:ceiling=min(ceiling,max(1,memory_bytes//(384*1024**2)))
    return max(1,min(24,ceiling,requested if requested!='auto' else ceiling))


def host_capacity(requested:str|int='auto')->dict[str,Any]:
    affinity=len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else os.cpu_count() or 1
    quota=None;memory=None
    # Walk the actual cgroup-v2 hierarchy: a service can have a tighter budget
    # than the root cgroup. Never modify host affinity, quota or nice settings.
    try:
        member=next(x.split(':',2)[2] for x in Path('/proc/self/cgroup').read_text().splitlines() if x.startswith('0::'))
        root=Path('/sys/fs/cgroup');path=root/member.lstrip('/')
        while path.is_relative_to(root):
            p=path/'cpu.max'
            if p.exists():
                q,period=p.read_text().split()
                if q!='max':quota=min(quota,float(q)/float(period)) if quota is not None else float(q)/float(period)
            p=path/'memory.max'
            if p.exists() and p.read_text().strip()!='max':memory=min(memory,int(p.read_text())) if memory is not None else int(p.read_text())
            if path==root:break
            path=path.parent
        available=next(int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
        memory=min(memory,available) if memory is not None else available
    except (OSError,StopIteration,ValueError):pass
    return dict(affinity_cpus=affinity,cgroup_cpu_quota=quota,available_memory_bytes=memory,worker_limit=worker_limit(affinity,quota=quota,memory_bytes=memory,requested=requested),requested=requested,reserved_cpu_slots=1 if affinity>1 else 0)


class ProjectionPool:
    def __init__(self,workers,*,executor_factory:Callable[...,Any]=ProcessPoolExecutor):
        if type(workers) is not int or workers<1:raise ValueError('Positive process capacity required')
        self.workers=workers;self.factory=executor_factory;self.executor=None;self.owner=get_ident()
        self.active={};self.waiting=OrderedDict();self.desired={};self.closed=False;self.failed=None
        self.counts=dict(submitted=0,completed=0,accepted=0,superseded=0,cancelled=0,worker_errors=0,coalesced=0)
        self.pids=set();self.cpu_seconds=0.;self.max_inflight=0
    def _check(self):
        if get_ident()!=self.owner:raise RuntimeError('Compute scheduling belongs to the core owner thread')
        if self.closed:raise RuntimeError('Compute pool is closed')
    def offer(self,lane,job):
        self._check()
        if self.failed:return False
        if self.desired.get(lane)==job['token']:return True
        if lane not in self.desired and len(self.desired)>=24:raise ValueError('At most the six-pair/four-frame projection cohort is permitted')
        if lane in self.waiting:self.counts['coalesced']+=1
        self.desired[lane]=job['token'];self.waiting[lane]=job
        self._dispatch();return True
    def _dispatch(self):
        if self.failed or self.closed:return
        for lane in list(self.waiting):
            if len(self.active)>=self.workers:break
            if lane in self.active:continue
            job=self.waiting.pop(lane)
            if self.executor is None:self.executor=self.factory(max_workers=self.workers,mp_context=get_context('spawn'))
            from .projection_math import compute_frame
            try:f=self.executor.submit(compute_frame,job)
            except Exception as e:self.failed=type(e).__name__;self.counts['worker_errors']+=1;self.waiting.clear();self.desired.clear();return
            self.active[lane]=(f,job);self.counts['submitted']+=1;self.max_inflight=max(self.max_inflight,len(self.active))
    def poll(self, *, max_results=None):
        self._check();ready=[]
        for lane,(future,job) in list(self.active.items()):
            if max_results is not None and len(ready)>=max_results:break
            if not future.done():continue
            del self.active[lane];self.counts['completed']+=1
            try:
                result=future.result()
                if result['token']!=job['token']:raise ValueError('Worker result/job identity mismatch')
                self.pids.add(result['pid']);self.cpu_seconds+=result['cpu_seconds']
                if self.desired.get(lane)!=job['token']:self.counts['superseded']+=1;continue
                self.desired.pop(lane,None);self.counts['accepted']+=1;ready.append((lane,job,result))
            except Exception as e:
                self.counts['worker_errors']+=1;self.failed=type(e).__name__;self.waiting.clear();self.desired.clear()
        self._dispatch();return ready
    def cancel(self,lane):
        self._check();self.waiting.pop(lane,None);self.desired.pop(lane,None)
    def invalidate(self,symbol):
        self._check()
        for lane in list(self.desired):
            if lane[0]==symbol:self.cancel(lane)
    def pending(self,lane):return lane in self.desired
    def metrics(self):
        return dict(self.counts,max_workers=self.workers,inflight=len(self.active),queued_lanes=len(self.waiting),pending_lanes=len(self.desired),max_inflight=self.max_inflight,observed_worker_pids=sorted(self.pids),worker_cpu_seconds=self.cpu_seconds,error=self.failed,closed=self.closed,lazy_not_started=self.executor is None)
    def close(self):
        if self.closed:return
        self._check();self.closed=True
        self.waiting.clear();self.desired.clear()
        for future,_ in self.active.values():
            if future.cancel():self.counts['cancelled']+=1
        # Jobs are bounded pure functions; wait joins every child and prevents
        # late results crossing the database/runtime lifetime boundary.
        if self.executor:self.executor.shutdown(wait=True,cancel_futures=True)
        self.active.clear()
