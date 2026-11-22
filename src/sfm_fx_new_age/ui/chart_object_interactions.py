"""Source-bound object geometry, group gestures and chart-local clipboard."""
from copy import deepcopy
from bisect import bisect_left
from datetime import timedelta
import math
from PySide6.QtCore import Qt,QPointF,QRectF
from PySide6.QtGui import QColor,QPen,QPolygonF,QFont,QFontMetricsF
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.chart_display import style_for,KINDS

class ObjectInteractionMixin:
    @staticmethod
    def _pen_style(name):return {'Solid':Qt.SolidLine,'Dash':Qt.DashLine,'Dot':Qt.DotLine,'Dash dot':Qt.DashDotLine}[name]
    def _frame_seconds(self):return {'W1':604800,'D1':86400,'H4':14400,'H1':3600}.get((self.data_identity or (None,)*4)[3],3600)
    def _time_index(self,stamp):
        times=[instant(r['open_time']) for r in self.bars];value=instant(stamp);i=bisect_left(times,value)
        if not times:return 0
        if len(times)==1:return (value-times[0]).total_seconds()/self._frame_seconds()
        if i==0:return (value-times[0]).total_seconds()/self._frame_seconds()
        if i==len(times):return len(times)-1+(value-times[-1]).total_seconds()/self._frame_seconds()
        return i-1+(value-times[i-1]).total_seconds()/max(1,(times[i]-times[i-1]).total_seconds())
    def _stamp_index(self,index):
        times=[instant(r['open_time']) for r in self.bars]
        if int(index)==index and 0<=index<len(times):return self.bars[int(index)]['open_time']
        if index<0:value=times[0]+timedelta(seconds=self._frame_seconds()*index)
        elif index>=len(times)-1:value=times[-1]+timedelta(seconds=self._frame_seconds()*(index-len(times)+1))
        else:
            i=max(0,min(len(times)-2,math.floor(index)));value=times[i]+(times[i+1]-times[i])*(index-i)
        return value.isoformat().replace('+00:00','Z')
    def _coordinates(self,anchor):
        area,rows,step,low,high,start=self._bounds;first=len(self.bars)-self.offset-len(rows)
        return QPointF(start+(self._time_index(anchor[0])-first+.5)*step,area.bottom()-(anchor[1]-low)/(high-low)*area.height())
    def _shape(self,obj):
        area=self._bounds[0];points=[self._coordinates(a) for a in obj['anchors']];a=points[0];style=style_for(obj)
        segments=[];labels=[];rectangle=None
        if obj['kind']=='Level':
            segments=[(QPointF(area.left(),a.y()),QPointF(area.right(),a.y()))];labels=[(QPointF(area.left()+5,a.y()-5),style['name'] or f"Level {obj['anchors'][0][1]:.{self.precision}f}")]
        elif obj['kind']=='Vertical':segments=[(QPointF(a.x(),area.top()),QPointF(a.x(),area.bottom()))]
        elif obj['kind']=='Text':labels=[(QPointF(a.x(),a.y()),style['text'])]
        else:
            b=points[1]
            if obj['kind'] in {'Rectangle','Ellipse','Triangle'}:
                rectangle=QRectF(a,b).normalized();tl,tr,bl,br=rectangle.topLeft(),rectangle.topRight(),rectangle.bottomLeft(),rectangle.bottomRight()
                if obj['kind']=='Triangle':
                    top=QPointF(rectangle.center().x(),rectangle.top());segments=[(bl,top),(top,br),(br,bl)]
                elif obj['kind']=='Ellipse':
                    center=rectangle.center();rx=rectangle.width()/2;ry=rectangle.height()/2
                    vertices=[QPointF(center.x()+rx*math.cos(n*math.pi/24),center.y()+ry*math.sin(n*math.pi/24)) for n in range(49)];segments=list(zip(vertices,vertices[1:]))
                else:segments=[(tl,tr),(tr,br),(br,bl),(bl,tl)]
            elif obj['kind']=='Fibonacci':
                left,right=sorted((a.x(),b.x()));left=area.left() if style['extend_left'] else left;right=area.right() if style['extend_right'] else right
                for ratio,price in self.drawings.fibonacci(obj):
                    y=area.bottom()-(price-self._bounds[3])/(self._bounds[4]-self._bounds[3])*area.height()
                    segments.append((QPointF(left,y),QPointF(right,y)));labels.append((QPointF(left+4,y-3),f'{ratio*100:g}%'+(f'  {price:.{self.precision}f}' if style['show_prices'] else '')))
                segments.append((a,b))
            else:
                if abs(b.x()-a.x())>.1:
                    slope=(b.y()-a.y())/(b.x()-a.x());aa=QPointF(area.left(),a.y()+(area.left()-a.x())*slope) if style['extend_left'] else a
                    bb=QPointF(area.right(),a.y()+(area.right()-a.x())*slope) if style['extend_right'] else b
                    if obj['kind']=='Ray' and not style['extend_left'] and not style['extend_right']:
                        edge=area.right() if b.x()>a.x() else area.left();bb=QPointF(edge,a.y()+(edge-a.x())*slope)
                    segments=[(aa,bb)]
                else:segments=[(a,b)]
        if style['name'] and obj['kind'] not in {'Level','Text'}:labels.insert(0,(QPointF(a.x()+5,a.y()-6),style['name']))
        if style['show_angle'] and obj['kind'] in {'Trend','Ray'}:
            angle=math.degrees(math.atan2(-(points[1].y()-a.y()),points[1].x()-a.x()));labels.append((QPointF(a.x()+5,a.y()+24),f'{angle:+.1f}° view angle'))
        return points,segments,labels,rectangle
    def _handles(self,obj):
        points,_,_,rect=self._shape(obj);result=list(enumerate(points))
        if rect:
            result += [(key,point) for key,point in (('nw',rect.topLeft()),('ne',rect.topRight()),('sw',rect.bottomLeft()),('se',rect.bottomRight()),
                ('n',QPointF(rect.center().x(),rect.top())),('s',QPointF(rect.center().x(),rect.bottom())),('e',QPointF(rect.right(),rect.center().y())),('w',QPointF(rect.left(),rect.center().y())))
                if all((point-existing).manhattanLength()>1 for existing in points)]
        return result
    def _text_rect(self,obj):
        p=self._coordinates(obj['anchors'][0]);s=style_for(obj);font=QFont(self.font());font.setPointSizeF(s['font_size']);font.setBold(s['bold'])
        fm=QFontMetricsF(font);return QRectF(p.x(),p.y()-fm.height(),min(360,max(60,max((fm.horizontalAdvance(t) for t in s['text'].splitlines()),default=0)+10)),max(20,fm.height()*min(8,len(s['text'].splitlines()) or 1)))
    def _label_rects(self,obj):
        style=style_for(obj)
        if not self.display['show_labels'] or not style['show_label']:return []
        font=QFont(self.font());font.setPointSizeF(style['font_size']);font.setBold(style['bold']);fm=QFontMetricsF(font)
        return [(text,self._text_rect(obj) if obj['kind']=='Text' else QRectF(pos.x(),pos.y()-fm.height(),min(360,max(60,fm.horizontalAdvance(text.split('\n')[0])+10)),max(20,fm.height()*min(8,len(text.splitlines()) or 1)))) for pos,text in self._shape(obj)[2]]
    def _resize_anchors(self,obj,handle,anchor):
        values=obj['anchors'];times=[self._time_index(t) for t,_ in values];prices=[v for _,v in values]
        left,right=min(times),max(times);bottom,top=min(prices),max(prices);x=self._time_index(anchor[0]);price=anchor[1]
        if 'w' in handle:left=x
        if 'e' in handle:right=x
        if 'n' in handle:top=price
        if 's' in handle:bottom=price
        return [(self._stamp_index(left),top),(self._stamp_index(right),bottom)]
    def _paint_drawings(self,p):
        if self.drawings.hidden or not self.display['show_drawings']:return
        label_rects=[]
        for obj in self.drawings.items+([self._draft] if self._draft else []):
            if obj['hidden']:continue
            style=style_for(obj);points,segments,labels,rect=self._shape(obj);color=QColor(style['color'])
            p.save();p.setPen(QPen(color,style['width'],self._pen_style(style['line_style'])));p.setBrush(Qt.NoBrush)
            if rect and style['fill']:
                fill=QColor(style['fill_color'] or style['color']);fill.setAlpha(round(style['opacity']*255/100));p.setBrush(fill)
                if obj['kind']=='Ellipse':p.drawEllipse(rect)
                elif obj['kind']=='Triangle':p.drawPolygon(QPolygonF([QPointF(rect.center().x(),rect.top()),rect.bottomRight(),rect.bottomLeft()]))
                else:p.drawRect(rect)
                p.setBrush(Qt.NoBrush)
            for a,b in segments:p.drawLine(a,b)
            if obj['id']==self._hover_object and obj['id'] not in self.drawings.selection:
                halo=QColor(self.display['selection_color']);halo.setAlpha(130);p.setPen(QPen(halo,max(3,style['width']+2),Qt.DotLine))
                for a,b in segments:p.drawLine(a,b)
                if obj['kind']=='Text':p.drawRect(self._text_rect(obj))
            if style['show_label'] and self.display['show_labels']:
                font=QFont(p.font());font.setPointSizeF(style['font_size']);font.setBold(style['bold']);p.setFont(font)
                for text,box in self._label_rects(obj):
                    if obj['kind']=='Text' or not any(box.intersects(old) for old in label_rects):
                        p.setPen(QColor(style['text_color'] or style['color']));p.fillRect(box,QColor(style['label_background'] or self.display['background']));p.drawText(box,Qt.AlignLeft|Qt.TextWordWrap,text);label_rects.append(box)
            if obj['id'] in self.drawings.selection:
                p.setPen(QPen(QColor(self.display['selection_color']),1));p.setBrush(QColor(self.display['background']))
                for _,point in self._handles(obj):p.drawRect(QRectF(point.x()-4,point.y()-4,8,8))
                if obj['locked']:p.drawText(QRectF(points[0].x()+8,points[0].y(),80,18),'Locked')
            p.restore()
        if self.drag and self.drag[0]=='select':
            p.save();p.setPen(QPen(QColor(self.display['selection_color']),1,Qt.DashLine));p.setBrush(Qt.NoBrush);p.drawRect(QRectF(self.drag[1],self.drag[2]).normalized());p.restore()
    def _hit_drawing(self,pos):
        if self.drawings.hidden or not self.display['show_drawings'] or not self._bounds or not self._bounds[0].contains(pos):return None
        # Keep resize handles deliberate; a generous body halo must not turn
        # an imprecise selection into an accidental resize. Distance wins over
        # paint order except for exact ties; filled interiors are a last resort.
        radius=self.display['hit_distance'];handles=[];edges=[];interiors=[]
        for obj in reversed(self.drawings.items):
            if obj['hidden'] or obj['id'] not in self.drawings.selection:continue
            for i,point in self._handles(obj):
                distance=math.hypot(pos.x()-point.x(),pos.y()-point.y())
                if distance<=min(9,radius):handles.append((distance,obj,i))
        if handles:
            _,obj,handle=min(handles,key=lambda row:row[0]);return obj,handle
        for obj in reversed(self.drawings.items):
            if obj['hidden']:continue
            points,segments,_,rect=self._shape(obj);style=style_for(obj)
            distance=min((self._distance(pos,a,b) for a,b in segments),default=math.inf)
            for _,box in self._label_rects(obj):
                dx=max(box.left()-pos.x(),0,pos.x()-box.right());dy=max(box.top()-pos.y(),0,pos.y()-box.bottom())
                distance=min(distance,math.hypot(dx,dy))
            if distance<=radius+style['width']/2:edges.append((distance,obj))
            if rect and style_for(obj)['fill'] and self.display['select_filled'] and rect.contains(pos):
                if obj['kind']=='Ellipse' and ((pos.x()-rect.center().x())/max(.001,rect.width()/2))**2+((pos.y()-rect.center().y())/max(.001,rect.height()/2))**2>1:continue
                if obj['kind']=='Triangle' and not QPolygonF([QPointF(rect.center().x(),rect.top()),rect.bottomRight(),rect.bottomLeft()]).containsPoint(pos,Qt.OddEvenFill):continue
                interiors.append(obj)
        if edges:return min(edges,key=lambda row:row[0])[1],None
        if interiors:return interiors[0],None
        return None
    def _anchor(self,pos,*,snap=False,mode=None):
        if not self._bounds or not self.bars or not self._bounds[0].contains(pos):return None
        area,rows,step,low,high,start=self._bounds;index=(pos.x()-start)/step-.5
        first=len(self.bars)-self.offset-len(rows);price=high-(pos.y()-area.top())/area.height()*(high-low)
        point=self._point(pos);mode=self.display['snap_mode'] if mode in {None,'Inherit'} else mode
        stamp=self._stamp_index(first+math.floor(index+.5))
        if snap and point and mode!='Off':
            i,_=point;row=rows[i]
            nearest=min((float(row[k]) for k in ('open','high','low','close')),key=lambda v:abs(v-price))
            if mode=='Always' or abs(nearest-price)/(self._bounds[4]-self._bounds[3])*self._bounds[0].height()<self.display['snap_distance']:price=nearest
        return stamp,price
    def copy_objects(self):
        self._clipboard=(self.data_identity,[deepcopy(o) for o in self.drawings.items if o['id'] in self.drawings.selection]);self.hovered.emit('Copied local objects; paste only within this source / frame')
    def paste_objects(self):
        if not self._clipboard or self._clipboard[0]!=self.data_identity:return
        objects=self._clipboard[1]
        if len(self.drawings.items)+len(objects)>100:self.hovered.emit('Object limit reached');return
        self.drawings.begin();ids=[]
        try:
            for obj in objects:
                from uuid import uuid4
                value=deepcopy(obj);value['id']=str(uuid4());value['locked']=False;self.drawings.items.append(value);ids.append(value['id'])
            self.drawings._selection=ids;self.drawings.commit()
        except ValueError:self.drawings.cancel()
    def nudge_objects(self,dx=0,dy=0):
        if not self.bars:return
        pip=(.01 if self.precision==3 else .0001)*self.display['nudge_pips'];dx*=self.display['nudge_bars'];self.drawings.begin()
        try:
            for obj in self.drawings.items:
                if obj['id'] in self.drawings.selection and not obj['locked']:
                    self.drawings.move(obj['id'],[(self._stamp_index(self._time_index(t)+dx),p+dy*pip) for t,p in obj['anchors']],remember=False)
            self.drawings.commit()
        except ValueError:self.drawings.cancel();self.hovered.emit('Movement refused: positive price required')
    def _new_object(self,kind,anchors):
        obj=self.drawings.add(kind,anchors,**self.display['drawing_defaults'].get(kind,{}))
        if self.display['one_shot']:self.tool='Pan';self.toolChanged.emit('Pan')
        if kind=='Text':self.editDrawing.emit(obj['id'])
        return obj
