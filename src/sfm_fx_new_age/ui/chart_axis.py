"""Truthful price-label rail: exact anchors, preserved ordering and no fake prices."""
from __future__ import annotations
import math


def price_ticks(low,high,pixels,spacing,precision):
    """Round human-readable *display* ticks, never quantize observed prices."""
    if not all(math.isfinite(v) for v in (low,high,pixels,spacing)) or high<=low or pixels<=0 or spacing<=0:return []
    raw=max((high-low)/max(1,pixels/spacing),10**(-precision))
    magnitude=10**math.floor(math.log10(raw))
    step=next(v*magnitude for v in (1,2,2.5,5,10) if v*magnitude>=raw*(1-1e-12))
    step=max(step,10**(-precision));first=math.ceil(low/step-1e-9)
    return [round(i*step,precision) for i in range(first,first+min(200,math.floor(high/step+1e-9)-first+1))
            if low<=round(i*step,precision)<=high]


def price_badges(entries,top,bottom,precision,*,label_height=18,coalesce=True,anchor_range=None):
    """Separate labels monotonically while retaining exact price-line anchors.

    Price-axis badges coalesce by default. Projection captions can retain each
    level's identity, including equal-price levels, and reserve a smaller label
    lane without dropping anchors in the rest of the actual plot.
    Insufficient space suppresses captions, never changes price coordinates.
    """
    if bottom-top<label_height:return []
    anchor_top,anchor_bottom=anchor_range or (top,bottom)
    groups=[]
    for actual_y,price,color,label in sorted(entries,key=lambda e:-e[1]):
        if not anchor_top<=actual_y<=anchor_bottom:continue
        if coalesce and groups and abs(price-groups[-1]['price'])<10**(-precision-1):groups[-1]['label']+='/'+label
        else:groups.append(dict(actual_y=actual_y,price=price,color=color,label=label))
    pitch=label_height+2;capacity=max(1,int((bottom-top+2)//pitch));groups=groups[:capacity]
    positions=[]
    for item in groups:positions.append(max(top,item['actual_y']-label_height/2,positions[-1]+pitch if positions else top))
    if positions:
        positions[-1]=min(positions[-1],bottom-label_height)
        for i in range(len(positions)-2,-1,-1):positions[i]=min(positions[i],positions[i+1]-pitch)
    return [dict(item,label_y=y) for item,y in zip(groups,positions)]
