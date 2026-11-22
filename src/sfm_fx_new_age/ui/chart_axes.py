"""Responsive chart-axis rails and source-bound measurement visuals; no data authority."""
from __future__ import annotations
import math
from PySide6.QtCore import Qt,QRectF,QPointF
from PySide6.QtGui import QColor,QPen,QFont,QFontMetricsF
from sfm_fx_new_age.contracts.domain import instant
from .chart_axis import price_ticks,price_badges


class ChartAxesMixin:
    def axis_font(self):
        font=QFont(self.font());font.setPointSizeF(self.display['axis_font_size']);return font

    def axis_metrics(self):return QFontMetricsF(self.axis_font())

    def price_axis_width(self):
        metrics=self.axis_metrics()
        sample=max((abs(float(r['high'])) for r in self.visible_bars()),default=1.0)
        return max(96,metrics.horizontalAdvance('C/B '+f'{sample:.{self.precision}f}')+22)

    def plot_rect(self):
        metrics=self.axis_metrics();rail=self.price_axis_width()
        axis_height=metrics.height()*2+12
        volume=self.display['volume_height'] if self.volume else 0
        return QRectF(10,30,max(1,self.width()-rail-14-self.projection_rail_width()),max(1,self.height()-30-axis_height-volume))

    def price_axis_rect(self):
        area=self.plot_rect();return QRectF(area.right(),area.top(),self.price_axis_width()+2,area.height())

    def time_axis_rect(self):
        area=self.plot_rect();top=area.bottom()+(self.display['volume_height'] if self.volume else 0)
        return QRectF(area.left(),top,area.width(),max(1,self.height()-top-2))

    def axis_at(self,pos):
        if self.price_axis_rect().contains(pos):return 'price'
        if self.time_axis_rect().contains(pos):return 'time'
        return None

    def price_axis_labels(self):
        if not self._bounds:return []
        area,_,_,low,high,_=self._bounds;metrics=self.axis_metrics();height=metrics.height()+6
        ticks=price_ticks(low,high,area.height(),max(self.display['price_tick_spacing'],height+8),self.precision)
        rail=self.price_axis_rect();labels=[]
        for value in reversed(ticks):
            y=area.bottom()-(value-low)/(high-low)*area.height()
            rect=QRectF(rail.left()+10,max(rail.top(),min(y-height/2,rail.bottom()-height)),max(1,rail.width()-16),height)
            labels.append({'value':value,'y':y,'text':f'{value:.{self.precision}f}','rect':rect})
        return labels

    def time_axis_labels(self):
        if not self._bounds:return []
        area,rows,step,_,_,start=self._bounds;rail=self.time_axis_rect();metrics=self.axis_metrics()
        mode=self.display['time_label_format'];labels=[];previous=area.left()-8
        # The axis contains only loaded observations. Empty future spaces have no
        # invented date ticks or session bars; their annotation policy is separate.
        target=max(self.display['time_tick_spacing'],metrics.horizontalAdvance('2026-11-08')+12)
        raw=max(1,target/step);magnitude=10**math.floor(math.log10(raw))
        stride=max(1,math.ceil(next(v*magnitude for v in (1,2,5,10) if v*magnitude>=raw)))
        indices=sorted({0,len(rows)-1,*range(0,len(rows),stride)})
        for i in indices:
            stamp=rows[i]['open_time'];dt=instant(stamp);frame=(self.data_identity or ('','','',''))[-1]
            first=dt.strftime('%Y-%m-%d') if mode=='ISO date + time' else dt.strftime('%d %b')
            second='' if mode=='Date only' else dt.strftime('%Y') if frame in {'D1','W1'} and mode=='Adaptive UTC' else dt.strftime('%H:%M')
            width=max(metrics.horizontalAdvance(first),metrics.horizontalAdvance(second))+12
            left=max(area.left()+2,min(start+(i+.5)*step-width/2,area.right()-width-2))
            if left<previous+8:continue
            rect=QRectF(left,rail.top()+5,width,max(1,rail.height()-8))
            labels.append({'stamp':stamp,'x':start+(i+.5)*step,'first':first,'second':second,'rect':rect})
            previous=rect.right()
        return labels

    def _paint_grid(self,p):
        if not self._bounds or not self.grid:return
        area=self.plot_rect();p.save();p.setClipRect(area)
        p.setPen(QPen(QColor(self.display['grid_color']),1,self._pen_style(self.display['grid_style'])))
        if self.display['grid_horizontal']:
            for tick in self.price_axis_labels():p.drawLine(QPointF(area.left(),tick['y']),QPointF(area.right(),tick['y']))
        if self.display['grid_vertical']:
            for tick in self.time_axis_labels():p.drawLine(QPointF(tick['x'],area.top()),QPointF(tick['x'],area.bottom()))
        p.restore()

    def ruler_readout(self):
        if not self.ruler or not self.bars:return None
        (t1,v1),(t2,v2)=self.ruler;indices={r['open_time']:i for i,r in enumerate(self.bars)}
        if t1 not in indices or t2 not in indices or not all(math.isfinite(v) and v>0 for v in (v1,v2)):return None
        mode=self.ruler_mode;bars=abs(indices[t2]-indices[t1]);hours=(instant(t2)-instant(t1)).total_seconds()/3600
        pips=(v2-v1)/(.01 if self.precision==3 else .0001);percent=(v2-v1)/v1*100
        sign='−' if hours<0 else '+';minutes=round(abs(hours)*60);days,remainder=divmod(minutes,1440);hh,mm=divmod(remainder,60)
        elapsed=sign+(str(days)+'d ' if days else '')+f'{hh}h {mm:02d}m'
        prices=f'{v1:.{self.precision}f} → {v2:.{self.precision}f}'
        times=instant(t1).strftime('%d %b %H:%M')+' → '+instant(t2).strftime('%d %b %H:%M')+' UTC'
        if mode=='price':lines=[f'PRICE RULER   {pips:+.1f} pips   {percent:+.2f}%',prices]
        elif mode=='time':lines=[f'TIME RULER   {bars} observed intervals   {elapsed}',times+' · gaps included']
        else:lines=[f'RANGE RULER   {pips:+.1f} pips   {percent:+.2f}%',f'{bars} observed intervals   {elapsed} · gaps included',prices]
        return dict(mode=mode,bars=bars,hours=hours,pips=pips,percent=percent,lines=lines,text='Measure: '+' · '.join(lines)+(' · bars' if mode=='range' else ''))

    def ruler_card_rect(self):
        result=self.ruler_readout()
        if not result or not self.display['show_ruler_card'] or not self._bounds:return None
        area=self.plot_rect();metrics=self.axis_metrics();width=min(area.width()-16,max(metrics.horizontalAdvance(line) for line in result['lines'])+24)
        height=min(area.height()-12,len(result['lines'])*(metrics.height()+3)+16)
        position=self.display['ruler_position'];left=area.right()-width-8 if position.endswith('right') else area.left()+8
        top=area.top()+6 if position.startswith('Top') else area.bottom()-height-6
        return QRectF(left,top,max(1,width),max(1,height))

    def _ruler_pixels(self):
        if not self.ruler_readout() or not self._bounds:return None
        area,rows,step,low,high,start=self._bounds;indices={r['open_time']:i for i,r in enumerate(rows)}
        if not all(t in indices for t,v in self.ruler):return None
        return [QPointF(start+(indices[t]+.5)*step,area.bottom()-(v-low)/(high-low)*area.height()) for t,v in self.ruler]

    def _paint_ruler(self,p):
        points=self._ruler_pixels()
        if not points:return
        a,b=points;area=self.plot_rect();color=QColor(self.display['ruler_color']);p.save();p.setClipRect(area)
        p.setPen(QPen(color,1.5));p.setBrush(Qt.NoBrush)
        if self.ruler_mode=='price':
            x=max(area.left()+8,min(a.x(),area.right()-8));p.drawLine(QPointF(x,a.y()),QPointF(x,b.y()))
            for y in (a.y(),b.y()):p.drawLine(QPointF(x-6,y),QPointF(x+6,y))
        elif self.ruler_mode=='time':
            tint=QColor(color);tint.setAlpha(14);p.fillRect(QRectF(min(a.x(),b.x()),area.top(),abs(a.x()-b.x()),area.height()),tint)
            y=area.bottom()-8;p.drawLine(QPointF(a.x(),y),QPointF(b.x(),y))
            for x in (a.x(),b.x()):p.drawLine(QPointF(x,y-6),QPointF(x,y+4))
        else:
            tint=QColor(color);tint.setAlpha(18);p.setBrush(tint);p.drawRect(QRectF(a,b).normalized());p.setBrush(Qt.NoBrush);p.drawLine(a,b)
        if self.display['show_ruler_guides']:
            p.setPen(QPen(color,1,Qt.DotLine))
            if self.ruler_mode!='time':
                for point in points:p.drawLine(QPointF(area.left(),point.y()),QPointF(area.right(),point.y()))
            if self.ruler_mode!='price':
                for point in points:p.drawLine(QPointF(point.x(),area.top()),QPointF(point.x(),area.bottom()))
        for point in points if self.ruler_mode!='time' else [QPointF(a.x(),area.bottom()-8),QPointF(b.x(),area.bottom()-8)]:
            p.setPen(QPen(color,1.5));p.setBrush(QColor(self.display['background']));p.drawEllipse(point,3,3)
        card=self.ruler_card_rect()
        if card:
            background=QColor(self.display['background']);background.setAlpha(244);p.setBrush(background);p.setPen(QPen(color,1));p.drawRoundedRect(card,5,5)
            p.setClipRect(card.adjusted(6,4,-6,-4));h=self.axis_metrics().height()+3
            for i,line in enumerate(self.ruler_readout()['lines']):
                rect=QRectF(card.left()+10,card.top()+6+i*h,card.width()-20,h)
                p.drawText(rect,Qt.AlignLeft|Qt.AlignVCenter,p.fontMetrics().elidedText(line,Qt.ElideRight,int(rect.width())))
        p.restore()

    def _axis_badges(self):
        if not self._bounds:return []
        area,rows,_,low,high,_=self._bounds;y=lambda value:area.bottom()-(float(value)-low)/(high-low)*area.height()
        entries=[(y(rows[-1]['close']),float(rows[-1]['close']),self.display['close_color'],'C')] if self.display['show_close'] else []
        for quote in self.quote_lines():entries.append((y(quote['price']),quote['price'],self.display[quote['side']+'_color'],quote['side'][0].upper()))
        if self._ruler_pixels() and self.ruler_mode!='time':
            for index,(_,value) in enumerate(self.ruler):entries.append((y(value),value,self.display['ruler_color'],'P'+str(index+1)))
        height=self.axis_metrics().height()+4
        return price_badges(entries,area.top(),area.bottom(),self.precision,label_height=height)

    def time_ruler_labels(self):
        points=self._ruler_pixels()
        if not points or self.ruler_mode=='price':return []
        area=self.plot_rect();rail=self.time_axis_rect();metrics=self.axis_metrics();items=[]
        for index,(point,(stamp,_)) in enumerate(zip(points,self.ruler)):
            dt=instant(stamp);first='T'+str(index+1)+' '+dt.strftime('%d %b');second=dt.strftime('%H:%M')
            width=max(metrics.horizontalAdvance(first),metrics.horizontalAdvance(second))+14
            items.append(dict(x=point.x(),first=first,second=second,width=width))
        items.sort(key=lambda item:item['x']);positions=[]
        if sum(item['width'] for item in items)+6>area.width()-4:return []
        for item in items:positions.append(max(area.left()+2,item['x']-item['width']/2,positions[-1]+items[0]['width']+4 if positions else area.left()+2))
        positions[-1]=min(positions[-1],area.right()-items[-1]['width']-2)
        positions[0]=min(positions[0],positions[-1]-items[0]['width']-4)
        return [dict(item,rect=QRectF(left,rail.top()+3,item['width'],rail.height()-5)) for item,left in zip(items,positions)]

    def _paint_axes(self,p):
        area=self.plot_rect();rail=self.price_axis_rect();time_rail=self.time_axis_rect();p.save();p.setFont(self.axis_font())
        bg=QColor(self.display['background']);fg=QColor(self.display['axis_color']);border=QColor(self.display['axis_border_color'])
        panel=QColor(self.display['axis_background_color'])
        if self.display['axis_panel']:p.fillRect(rail,panel);p.fillRect(time_rail,panel)
        axis=self.axis_at(self.mouse) if self.mouse else None
        if axis and self.display['show_axis_highlight']:
            tint=QColor(fg);tint.setAlpha(15);p.fillRect(rail if axis=='price' else time_rail,tint)
        p.setPen(QPen(border,1));p.drawLine(QPointF(area.right(),area.top()),QPointF(area.right(),area.bottom()));p.drawLine(time_rail.topLeft(),time_rail.topRight())
        metrics=self.axis_metrics();badges=self._axis_badges() if self._bounds else [];occupied=[]
        for badge in badges:occupied.append(QRectF(rail.left()+8,badge['label_y'],rail.width()-12,metrics.height()+4))
        for tick in self.price_axis_labels():
            p.setPen(QPen(fg,1));p.drawLine(QPointF(rail.left(),tick['y']),QPointF(rail.left()+5,tick['y']))
            if not any(tick['rect'].intersects(rect) for rect in occupied):p.drawText(tick['rect'],Qt.AlignRight|Qt.AlignVCenter,tick['text'])
        if self.display['axis_minor_ticks']:
            ticks=self.price_axis_labels()
            for a,b in zip(ticks,ticks[1:]):
                y=(a['y']+b['y'])/2;p.setPen(QPen(border,1));p.drawLine(QPointF(rail.left(),y),QPointF(rail.left()+3,y))
        labels=self.time_axis_labels();ruler_labels=self.time_ruler_labels()
        for tick in labels:
            p.setPen(fg);p.drawLine(QPointF(tick['x'],time_rail.top()),QPointF(tick['x'],time_rail.top()+4))
            if any(tick['rect'].intersects(v['rect']) for v in ruler_labels):continue
            rect=tick['rect'];p.drawText(QRectF(rect.left(),rect.top(),rect.width(),metrics.height()+1),Qt.AlignHCenter|Qt.AlignVCenter,tick['first'])
            if tick['second']:
                muted=QColor(fg);muted.setAlpha(175);p.setPen(muted);p.drawText(QRectF(rect.left(),rect.top()+metrics.height(),rect.width(),metrics.height()+1),Qt.AlignHCenter|Qt.AlignVCenter,tick['second'])
        if self.display['axis_minor_ticks'] and self._bounds:
            _,rows,step,_,_,start=self._bounds
            stride=max(1,math.ceil(10/step));p.setPen(border)
            for i in range(0,len(rows),stride):
                x=start+(i+.5)*step;p.drawLine(QPointF(x,time_rail.top()),QPointF(x,time_rail.top()+2))
        p.setPen(fg);p.drawText(QRectF(rail.left()+2,time_rail.top()+4,rail.width()-4,time_rail.height()-4),Qt.AlignCenter,'UTC')
        for badge,rect in zip(badges,occupied):
            p.setPen(QPen(QColor(badge['color']),1));p.drawLine(QPointF(area.right(),badge['actual_y']),QPointF(rect.left(),rect.center().y()))
            self._tag(p,rect,f"{badge['label']} {badge['price']:.{self.precision}f}",badge['color'])
        for tick in ruler_labels:
            rect=tick['rect'];color=QColor(self.display['ruler_color']);p.setPen(QPen(color,1))
            p.drawLine(QPointF(tick['x'],area.bottom()),QPointF(rect.center().x(),rect.top()))
            p.fillRect(rect,bg);p.setBrush(Qt.NoBrush);p.drawRoundedRect(rect,3,3)
            for i,key in enumerate(('first','second')):p.drawText(QRectF(rect.left(),rect.top()+1+i*metrics.height(),rect.width(),metrics.height()+2),Qt.AlignCenter,tick[key])
        if self.crosshair and self.mouse and self._point(self.mouse):
            i,price=self._point(self.mouse);height=metrics.height()+6
            rect=QRectF(rail.left()+3,max(rail.top(),min(self.mouse.y()-height/2,rail.bottom()-height)),rail.width()-6,height)
            self._tag(p,rect,f'{price:.{self.precision}f}',self.display['crosshair_color'])
            date=instant(self._bounds[1][i]['open_time']).strftime('%Y-%m-%d %H:%M UTC');width=min(area.width()-4,metrics.horizontalAdvance(date)+16)
            rect=QRectF(max(area.left()+2,min(self.mouse.x()-width/2,area.right()-width-2)),time_rail.top()+3,width,time_rail.height()-5)
            self._tag(p,rect,date,self.display['crosshair_color'])
        p.restore()

    def clear_ruler(self):
        self.ruler=None;self.ruler_mode='range';self.update();self.hovered.emit('Measurement cleared · chart data and drawings unchanged')

    def _begin_ruler(self,pos,mode):
        if not self._bounds:return False
        area,rows,step,low,high,start=self._bounds
        x=pos.x() if mode!='price' else min(area.right()-self.display['right_margin']*step-step/2,max(area.left()+step/2,area.center().x()))
        point=self._point(QPointF(x,max(area.top(),min(pos.y(),area.bottom()))))
        if not point:self.hovered.emit('Time ruler requires a loaded observed candle; no future dates are invented.');return False
        index,value=point
        if mode=='time':value=(low+high)/2
        if value<=0:self.hovered.emit('Measurement requires a positive price range; reset the price scale.');return False
        self.ruler_mode=mode;anchor=(rows[index]['open_time'],value);self.ruler=(anchor,anchor);self.drag=('ruler',);self.update();return True

    def _move_ruler(self,pos):
        if not self.ruler or not self._bounds:return
        area,rows,_,low,high,_=self._bounds;first=self.ruler[0]
        if self.ruler_mode=='price':anchor=(first[0],high-(max(area.top(),min(pos.y(),area.bottom()))-area.top())/area.height()*(high-low))
        else:
            point=self._point(QPointF(pos.x(),max(area.top(),min(pos.y(),area.bottom()))))
            if not point:return
            index,value=point;anchor=(rows[index]['open_time'],first[1] if self.ruler_mode=='time' else value)
        if anchor[1]<=0:return
        self.ruler=(first,anchor);self.hovered.emit(self.ruler_readout()['text'])
