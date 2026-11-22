"""Bounded human drawings; timestamps/prices, reversible edits, no network/runtime."""
from copy import deepcopy
from uuid import uuid4
from sfm_fx_new_age.contracts.chart_display import KINDS,OBJECT_STYLE,validate_drawing,validate_style,anchor_count,style_for

class DrawingBook:
    LIMIT=100
    def __init__(self,changed=lambda:None):
        self.items=[];self._selection=[];self.hidden=False;self._undo=[];self._redo=[];self.changed=changed;self._gesture=None
    @property
    def selected(self):return self._selection[-1] if self._selection else None
    @selected.setter
    def selected(self,value):self._selection=[value] if value else []
    @property
    def selection(self):return [i for i in self._selection if self.get(i)]
    def select(self,identity,additive=False):
        if not self.get(identity):self.selected=None;return
        if additive:
            if identity in self._selection:self._selection.remove(identity)
            else:self._selection.append(identity)
        else:self.selected=identity
    @property
    def can_undo(self):return bool(self._undo)
    @property
    def can_redo(self):return bool(self._redo)
    def checkpoint(self):self._undo=(self._undo+[deepcopy(self.items)])[-64:];self._redo=[]
    def begin(self):
        if self._gesture is None:self._gesture=deepcopy(self.items)
    def commit(self):
        before=self._gesture;self._gesture=None
        if before is not None and before!=self.items:self._undo=(self._undo+[before])[-64:];self._redo=[];self.changed()
    def cancel(self):
        if self._gesture is not None:self.items=self._gesture;self._gesture=None;self.changed()
    def undo(self):
        self.cancel()
        if self._undo:self._redo.append(deepcopy(self.items));self.items=self._undo.pop();self.selected=None;self.changed()
    def redo(self):
        self.cancel()
        if self._redo:self._undo.append(deepcopy(self.items));self.items=self._redo.pop();self.selected=None;self.changed()
    @staticmethod
    def anchors(values):
        probe={'id':'probe','kind':'Level' if len(values)==1 else 'Trend','anchors':values,'color':'#F4C66B','hidden':False,'locked':False}
        validate_drawing(probe);return [(t,float(v)) for t,v in values]
    def add(self,kind,anchors,**properties):
        if kind not in KINDS:raise ValueError('Unsupported drawing')
        obj={'id':str(uuid4()),'kind':kind,'anchors':self.anchors(anchors),'color':'#F4C66B','locked':False,'hidden':False}|validate_style(properties)
        validate_drawing(obj)
        if len(self.items)>=self.LIMIT:raise ValueError('Local drawing limit reached; remove an object')
        if self._gesture is None:self.checkpoint()
        self.items.append(obj);self.selected=obj['id'];self.changed();return obj
    def get(self,identity):return next((d for d in self.items if d['id']==identity),None)
    def modify(self,identity,**values):return self.modify_many([identity],**values)
    def modify_many(self,identities,**values):
        if set(values)-set(OBJECT_STYLE)-{'locked','hidden'}:raise ValueError('Unknown local drawing setting')
        validate_style({k:v for k,v in values.items() if k in OBJECT_STYLE})
        for k in ('locked','hidden'):
            if k in values and type(values[k]) is not bool:raise ValueError('Boolean drawing flag required')
        objects=[o for o in self.items if o['id'] in identities]
        if not objects or all(all(o.get(k,OBJECT_STYLE.get(k))==v for k,v in values.items()) for o in objects):return False
        if self._gesture is None:self.checkpoint()
        for obj in objects:obj.update(deepcopy(values))
        self.changed();return True
    def replace(self,identity,anchors,properties):
        obj=self.get(identity)
        if not obj:return False
        values=validate_style(properties);candidate=dict(obj,**values)
        if not obj['locked']:candidate['anchors']=self.anchors(anchors)
        elif list(anchors)!=list(obj['anchors']):raise ValueError('Unlock before changing coordinates')
        validate_drawing(candidate)
        # Do not expand absent defaults or normalize untouched anchors merely by
        # opening and applying a properties dialog.
        candidate={k:v for k,v in candidate.items() if k in obj or k not in OBJECT_STYLE or v!=OBJECT_STYLE[k]}
        if candidate==obj:return False
        self.checkpoint();obj.update(candidate);self.changed();return True
    def move(self,identity,anchors,*,remember=True):
        obj=self.get(identity)
        if not obj or obj['locked']:return False
        anchors=self.anchors(anchors)
        if len(anchors)!=len(obj['anchors']):raise ValueError('Preserve drawing topology')
        if anchors==obj['anchors']:return False
        if remember and self._gesture is None:self.checkpoint()
        obj['anchors']=anchors;self.changed();return True
    def duplicate(self,identities=None):
        originals=[deepcopy(o) for o in self.items if o['id'] in (identities or self.selection)]
        if len(self.items)+len(originals)>self.LIMIT:raise ValueError('Local drawing limit reached')
        if not originals:return []
        if self._gesture is None:self.checkpoint()
        for o in originals:
            o['id']=str(uuid4());o['locked']=False;o['name']=(style_for(o)['name']+' copy').strip()[:80];self.items.append(o)
        self._selection=[o['id'] for o in originals];self.changed();return originals
    def reorder(self,identities,front=True):
        chosen=[o for o in self.items if o['id'] in identities];rest=[o for o in self.items if o['id'] not in identities]
        order=rest+chosen if front else chosen+rest
        if order!=self.items:self.checkpoint();self.items=order;self.changed()
    def delete(self,identity=None):self.delete_many([identity] if identity else self.selection)
    def delete_many(self,identities):
        if not any(o['id'] in identities for o in self.items):return
        self.checkpoint();self.items=[o for o in self.items if o['id'] not in identities];self._selection=[i for i in self._selection if self.get(i)];self.changed()
    def clear(self):
        if self.items:self.checkpoint();self.items=[];self.selected=None;self.changed()
    @staticmethod
    def fibonacci(obj):
        first,second=(a[1] for a in obj['anchors'])
        return [(r,second+(first-second)*r) for r in style_for(obj)['fib_levels']]
