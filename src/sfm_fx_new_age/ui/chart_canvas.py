"""Source-bound chart interaction/rendering. View studies and drawings never publish signals."""
from __future__ import annotations
import math
from copy import deepcopy
from bisect import bisect_left
from PySide6.QtCore import Qt,QRectF,QPointF,Signal
from PySide6.QtGui import QPainter,QColor,QPen,QPainterPath,QFont
from PySide6.QtWidgets import QWidget,QSizePolicy,QMenu
from sfm_fx_new_age.contracts.domain import instant
from .chart_objects import DrawingBook
from .chart_interactions import ChartInteractionMixin
from .chart_axis import price_badges
from .chart_axes import ChartAxesMixin
from .chart_public_strategies import PublicStrategyPaintMixin
from .chart_projection_layout import ProjectionCaptionMixin
from sfm_fx_new_age.contracts.chart_display import DISPLAY_DEFAULTS,validate_display


class CandleCanvas(ProjectionCaptionMixin,PublicStrategyPaintMixin,ChartAxesMixin,ChartInteractionMixin,QWidget):
    hovered=Signal(str)
    viewChanged=Signal()
    toolChanged=Signal(str)
    optionsChanged=Signal()
    manageDrawings=Signal()
    editDrawing=Signal(str)
    editSelection=Signal()
    settingsRequested=Signal()
    axisSettingsRequested=Signal()
    colourSettingsRequested=Signal()
    selectionSettingsRequested=Signal()
    publicDetailsRequested=Signal()
    projectionDisplayChanged=Signal()
    periodStepped=Signal(int)
    inspected=Signal(object)
    evidenceSelected=Signal(str)
    def __init__(self,parent=None):
        super().__init__(parent);self.setObjectName('forexChart');self.setMinimumSize(300,120)
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding);self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus);self.setAccessibleName('Read-only forex chart; arrows pan, plus/minus zoom, End latest, Home oldest')
        self.bars=[];self.levels=[];self.title='';self.empty='Open connection settings to load broker history'
        self.grid=True;self.crosshair=True;self.volume=False;self.style='Candles';self.studies=set()
        self.window=80;self.offset=0;self.mouse=None;self.drag=None;self.precision=5;self._bounds=None
        self.data_identity=None;self.price_range=None;self.tool='Pan';self.ruler=None;self.ruler_mode='range'
        self.drawings=DrawingBook(self._objects_changed);self._draft=None
        self.show_bid=False;self.show_ask=False;self.wheel_mode='Zoom'
        self.display=deepcopy(DISPLAY_DEFAULTS);self._clipboard=None;self._hover_object=None
        self._memory={};self._study_values={};self._quotes={};self.follow=True;self.forming=None
        self.setToolTip('Measure → Time / Price / Range ruler · Shift+drag axis: measure that axis · plain axis drag: scale · double-click axis: reset · right-click axis: settings · Escape: clear measurement')
        self.broker_visuals=[];self._research_regions=[];self.setup_projections=[];self.scenario_projection:dict|None=None
        self.strategy_layers=[];self.public_filters_applied=False
        self.projection_focus=None;self.projection_page=0

    def known_x(self,stamp):
        """Availability maps to time, never full-width retroactive knowledge."""
        area,rows,step,low,high,start=self._bounds;target=instant(stamp)
        # Bounds are replaced for every paint/data/view change. This cache owns
        # only screen geometry; it never changes timestamps or source authority.
        if getattr(self,'_time_bounds',None) is not self._bounds:
            self._time_bounds=self._bounds
            self._time_open=[instant(r['open_time']) for r in rows]
            self._time_close=[instant(r.get('close_time',r['open_time'])) for r in rows]
            self._time_coordinates={}
        if target in self._time_coordinates:return self._time_coordinates[target]
        i=bisect_left(self._time_close,target)
        if i==len(rows):value=start+len(rows)*step
        elif target<=self._time_open[i]:value=start+i*step
        elif target==self._time_close[i]:value=start+(i+1)*step
        else:
            opened,closed=self._time_open[i],self._time_close[i]
            value=start+(i+(target-opened).total_seconds()/max(1,(closed-opened).total_seconds()))*step
        if len(self._time_coordinates)<4096:self._time_coordinates[target]=value
        return value

    def region_end_x(self,stamp):
        # An expiry beyond observed history is not a fabricated candle/time
        # coordinate. Continue the hypothesis into the view margin instead of
        # collapsing its start and future expiry onto the same last-bar edge.
        assert self._bounds is not None
        area,rows,*_=self._bounds
        return area.right() if instant(stamp)>instant(rows[-1]['close_time']) else self.known_x(stamp)

    def research_regions(self):
        if not self._bounds:return []
        area,rows,step,low,high,start=self._bounds;regions=[]
        for level in self.levels[:100]:
            try:
                line=level['lineage']
                if self.public_filters_applied and line['method_version']=='SFM_OB_CLOSED_PIVOT_RESEARCH_V1' and not any(v['strategy_id']=='order_block' for v in self.visible_public_strategy_layers()):continue
                if line['timeframe'] not in self.display['projection_frames']:continue
                if (line['source_scope'],line['source_epoch'],line['symbol'])!=self.data_identity[:3] or level.get('state') not in {'ACTIVE','CONFIRMED','TOUCHED'}:continue
                if self.offset and instant(line['available_at'])>instant(rows[-1]['close_time']):continue
                x=max(area.left(),self.known_x(line['available_at']));end=min(area.right(),self.region_end_x(level['expires_at'])) if level.get('expires_at') else area.right()
                y=lambda v:area.bottom()-(float(v)-low)/(high-low)*area.height()
                if end<=x:continue
                rect=QRectF(x,y(level['high']),end-x,max(2,y(level['low'])-y(level['high'])))
                regions.append((level,rect))
            except (KeyError,ValueError,TypeError):continue
        return regions

    def projection_lines(self):
        if not self._bounds:return []
        area,rows,step,low,high,start=self._bounds;result=[]
        projections=list(self.setup_projections[:100]) if self.display['show_setups'] else []
        scenario=self.scenario_projection
        if scenario is not None and self.display['show_scenarios']:projections.append(scenario)
        for projection in projections:
            if (projection['scope_id'],projection['source_epoch'],projection['symbol'])!=self.data_identity[:3]:continue
            frame=projection['source_timeframe']
            if frame and frame not in self.display['projection_frames']:continue
            stamp=projection['available_at']
            if self.offset and instant(stamp)>instant(rows[-1]['close_time']):continue
            left=max(area.left(),self.known_x(stamp));right=min(area.right(),self.region_end_x(projection['expires_at'])) if projection.get('expires_at') else area.right()
            if right<=left:continue
            for line in projection['lines']:
                yy=area.bottom()-(float(line['price'])-low)/(high-low)*area.height()
                if area.top()<=yy<=area.bottom():result.append((projection,line,left,right,yy))
        return result

    def _projection_badge_entries(self):
        area=self.plot_rect();entries=[]
        if self.display['show_research']:
            for level,rect in self.research_regions():
                entries.append((rect.top(),float(level['high']),self.display['research_color'],level['kind']+' · '+level['lineage']['timeframe']))
        for projection,line,left,right,yy in self.projection_lines():
            color=self.display['scenario_color' if projection['category']=='MANUAL_SCENARIO' else 'setup_color']
            frame=projection['source_timeframe'] or 'frame unknown'
            label=projection['category'].replace('_',' ').title()+' · '+frame+' · '+line['role']+' '+line['price']
            if projection.get('expired'):label+=' · expired geometry'
            if projection.get('object_id'):label+=' · '+projection['object_id'][:18]
            entries.append((yy,float(line['price']),color,label))
        entries.extend(self.public_strategy_badge_entries())
        return entries

    def _paint_projections(self,p):
        area=self.plot_rect()
        for projection,line,left,right,yy in self.projection_lines():
            color=self.display['scenario_color' if projection['category']=='MANUAL_SCENARIO' else 'setup_color']
            p.setPen(QPen(QColor(color),1,Qt.DashDotLine));p.setBrush(Qt.NoBrush)
            p.drawLine(QPointF(left,yy),QPointF(right,yy))


    @property
    def horizontal(self):return [d['anchors'][0][1] for d in self.drawings.items if d['kind']=='Level']
    @horizontal.setter
    def horizontal(self,values):
        stamp=self.bars[-1]['open_time'] if self.bars else '2000-01-01T00:00:00Z'
        self.drawings.checkpoint();self.drawings.items=[d for d in self.drawings.items if d['kind']!='Level']
        for value in values:self.drawings.add('Level',[(stamp,value)])
        self._objects_changed()
    def _objects_changed(self):
        self.update()
        if not self.drag or self.drag[0]!='object':self.viewChanged.emit()
    def set_display(self,values):
        self.display.update(validate_display(values));self._bounds=None;self.update();self.optionsChanged.emit()

    def _remember(self):
        if self.data_identity is not None:
            self._memory[self.data_identity]=(self.window,self.offset,self.price_range,self.drawings,self.follow)
            if len(self._memory)>64:self._memory.pop(next(iter(self._memory)))

    def set_data(self,rows,title,identity,*,empty='',levels=(),studies=None):
        safe=[]
        for row in rows:
            try:
                values=[float(row[k]) for k in ('open','high','low','close')];instant(row['open_time'])
                if not all(math.isfinite(v) and v>0 for v in values):continue
                if values[1]<max(values[0],values[3]) or values[2]>min(values[0],values[3]):continue
                safe.append(dict(row))
            except (KeyError,TypeError,ValueError):continue
        safe.sort(key=lambda r:instant(r['open_time']))
        if identity!=self.data_identity:
            self.projection_focus=None;self.projection_page=0
            self.drawings.cancel()
            self._remember();self.data_identity=identity
            self.window,self.offset,self.price_range,self.drawings,self.follow=self._memory.get(identity,(80,0,None,DrawingBook(self._objects_changed),True))
            self.mouse=None;self.ruler=None;self.ruler_mode='range';self.drag=None;self.forming=None;self._hover_object=None
            self._quotes={};self._draft=None;self._clipboard=None;self.setup_projections=[];self.scenario_projection=None;self.broker_visuals=[]
            self.strategy_layers=[]
        elif self.offset and self.bars:
            # Keep the same right-edge candle when new bars arrive during inspection.
            anchor=self.visible_bars()[-1]['open_time'] if self.visible_bars() else None
            positions={r['open_time']:i for i,r in enumerate(safe)}
            if anchor in positions:self.offset=len(safe)-positions[anchor]-1
        self.bars=safe;self.levels=list(levels);self.title=title;self.empty=empty
        self.precision=3 if 'JPY' in title else 5
        self.offset=min(self.offset,max(0,len(safe)-1));self._bounds=None
        self._study_values=studies or {}
        self.update();self.viewChanged.emit()

    def set_quotes(self,quote):self._quotes=quote;self.update()
    def set_forming(self,row):
        self.forming=None
        if row and len(self.data_identity or ())==4:
            scope,epoch,symbol,frame=self.data_identity
            if (row.get('scope_id'),row.get('source_epoch'),row.get('symbol'),row.get('timeframe'))==(scope,epoch,symbol,frame):
                try:
                    values=[float(row[k]) for k in ('open','high','low','close')];instant(row['open_time'])
                    if self.bars and instant(row['open_time'])<instant(self.bars[-1].get('close_time',self.bars[-1]['open_time'])):return
                    if all(math.isfinite(v) and v>0 for v in values) and values[2]<=min(values[0],values[3])<=max(values[0],values[3])<=values[1]:self.forming=dict(row)
                except (KeyError,TypeError,ValueError):pass
        self.update()
    def fit(self):
        self.offset=0;self.window=min(100,max(20,len(self.bars)));self.price_range=None;self.follow=True
        self.update();self.viewChanged.emit()
    def latest(self):self.offset=0;self.follow=True;self.update();self.viewChanged.emit()
    def pan(self,amount):
        self.offset=max(0,min(max(0,len(self.bars)-self.window),self.offset+amount));self.follow=self.offset==0
        self.update();self.viewChanged.emit()
    def zoom(self,factor,position=None):
        old=self.window;new=max(8,min(2000,round(old*factor)))
        if new==old:return
        if position is not None and self._bounds and len(self.bars)>=old:
            area,rows,step,_,_,start=self._bounds
            ratio=max(0,min(1,(position.x()-area.left())/area.width()))
            old_index=(position.x()-start)/step
            anchor=len(self.bars)-self.offset-len(rows)+math.floor(old_index)
            new_index=math.floor(ratio*max(new+self.display['right_margin'],12))
            self.offset=max(0,min(max(0,len(self.bars)-new),len(self.bars)-anchor-new+new_index))
        self.window=new;self.follow=self.offset==0;self.update();self.viewChanged.emit()
    def go_to(self,stamp):
        if not self.bars:return False
        target=instant(stamp);times=[instant(r['open_time']) for r in self.bars]
        if target<times[0] or target>times[-1]:return False
        i=bisect_left(times,target);end=min(len(times),i+self.window//2+1)
        self.offset=min(max(0,len(times)-self.window),max(0,len(times)-end));self.follow=self.offset==0;self.update();self.viewChanged.emit();return True

    def visible_bars(self):
        end=max(0,len(self.bars)-self.offset);return self.bars[max(0,end-self.window):end]
    def _point(self,pos):
        if not self._bounds:return None
        area,rows,step,low,high,start=self._bounds
        if not area.contains(pos):return None
        index=(pos.x()-start)/step
        if not 0<=index<len(rows):return None
        i=int(index)
        return i,high-(pos.y()-area.top())/area.height()*(high-low)
    def _tag(self,p,rect,text,color):
        background=QColor(self.display['background']);p.fillRect(rect,background);p.setPen(QPen(QColor(color),1));p.setBrush(Qt.NoBrush);p.drawRoundedRect(rect.adjusted(.5,.5,-.5,-.5),3,3);p.drawText(rect,Qt.AlignCenter,text)

    def paintEvent(self,event):
        painter=QPainter(self)
        try:self._paint_chart(painter)
        finally:painter.end()

    def _paint_chart(self,p):
        p.setRenderHint(QPainter.Antialiasing);p.fillRect(self.rect(),QColor(self.display['background']))
        p.setFont(self.axis_font())
        area=self.plot_rect();p.setPen(QColor(self.display['foreground']))
        if self.display['show_title']:
            p.setPen(QColor(self.display['title_color']))
            width=max(1,area.width()-165*len(self.studies) if self.display['show_study_legend'] else area.width())
            p.drawText(QRectF(12,1,width,25),Qt.AlignLeft|Qt.AlignVCenter,p.fontMetrics().elidedText(self.title,Qt.ElideRight,int(width)))
        rows=self.visible_bars()
        if not rows:
            self._bounds=None;self._paint_axes(p);p.drawText(area.adjusted(12,4,-12,-4),Qt.AlignCenter|Qt.TextWordWrap,self.empty);return
        low=min(float(r['low']) for r in rows);high=max(float(r['high']) for r in rows)
        if self.forming and self.offset==0 and self.display['show_forming']:
            low=min(low,float(self.forming['low']));high=max(high,float(self.forming['high']))
        pad=max((high-low)*self.display['price_padding']/100,high*.00005);low-=pad;high+=pad
        if self.price_range:low,high=self.price_range
        y=lambda price:area.bottom()-(float(price)-low)/(high-low)*area.height()
        # Right breathing room without making sparse histories into giant candles.
        step=area.width()/max(len(rows)+self.display['right_margin'],12);start=area.left()+(area.width()-len(rows)*step)/2 if len(rows)<12 else area.left()
        self._bounds=(area,rows,step,low,high,start)
        self._paint_grid(p)
        p.save();p.setClipRect(area)
        self._research_regions=self.research_regions() if self.display['show_research'] else []
        for level,rect in self._research_regions:
            color=QColor(self.display['research_color']);color.setAlpha(24);p.fillRect(rect,color)
        line=QPainterPath()
        for i,row in enumerate(rows):
            x=start+(i+.5)*step;up=float(row['close'])>=float(row['open']);color=QColor(self.display['bull_color'] if up else self.display['bear_color'])
            p.setPen(QPen(QColor(self.display['bull_wick_color' if up else 'bear_wick_color']),self.display['wick_width']));p.setBrush(color)
            if self.style=='Dot':
                p.setBrush(QColor(self.display['line_color']));p.setPen(Qt.NoPen);p.drawEllipse(QPointF(x,y(row['close'])),self.display['dot_radius'],self.display['dot_radius'])
            elif self.style=='Line':
                if i:line.lineTo(x,y(row['close']))
                else:line.moveTo(x,y(row['close']))
            else:
                p.drawLine(QPointF(x,y(row['high'])),QPointF(x,y(row['low'])))
                width=min(step*self.display['candle_width']/200,12)
                if self.style=='OHLC':
                    p.drawLine(QPointF(x-width,y(row['open'])),QPointF(x,y(row['open'])))
                    p.drawLine(QPointF(x,y(row['close'])),QPointF(x+width,y(row['close'])))
                else:
                    p.setPen(QPen(QColor(self.display['bull_border_color' if up else 'bear_border_color']),self.display['wick_width']))
                    p.setBrush(color if self.display['bull_filled' if up else 'bear_filled'] else QColor(self.display['background']))
                    p.drawRect(QRectF(x-width,min(y(row['open']),y(row['close'])),max(1,width*2),max(1,abs(y(row['open'])-y(row['close'])))))
        p.setBrush(Qt.NoBrush) # Open QPainterPaths must never inherit candle fill.
        if self.style=='Line':p.setPen(QPen(QColor(self.display['line_color']),self.display['line_width']));p.drawPath(line)
        if self.forming and self.offset==0 and self.display['show_forming']:
            row=self.forming;x=start+(len(rows)+.5)*step
            p.setPen(QPen(QColor(self.display['forming_color']),1,Qt.DashLine));p.setBrush(Qt.NoBrush)
            p.drawLine(QPointF(x,y(row['high'])),QPointF(x,y(row['low'])))
            p.drawRect(QRectF(x-min(step*.3,7),min(y(row['open']),y(row['close'])),max(1,min(step*.6,14)),max(1,abs(y(row['open'])-y(row['close'])))))
            p.drawText(QRectF(area.left()+6,area.top()+4,300,18),Qt.AlignLeft,'Forming · partial observation; not a closed candle')
        start_index=len(self.bars)-self.offset-len(rows)
        for name,color in (('SMA 20',self.display['sma_color']),('EMA 50',self.display['ema_color'])):
            if name not in self.studies:continue
            path=QPainterPath();begun=False
            for i,v in enumerate(self._study_values.get(name,[])[start_index:start_index+len(rows)]):
                if v is None:continue
                x=start+(i+.5)*step
                if begun:path.lineTo(x,y(v))
                else:path.moveTo(x,y(v));begun=True
            p.setPen(QPen(QColor(color),1.5));p.drawPath(path)
        self._paint_drawings(p)
        self._paint_public_strategies(p)
        self._paint_projections(p)
        for index,row in enumerate(self.broker_visuals[:50] if self.display['show_broker'] else []):
            try:
                yy=y(row['entry_price'])
                if not area.top()<=yy<=area.bottom():continue
                stamp=row.get('observed_at') or row.get('created_at');left=max(area.left(),self.known_x(stamp)) if stamp else area.right()-30
                color=self.display['local_order_color' if row['category'].startswith('Local') else 'broker_color'];p.setPen(QPen(QColor(color),1,Qt.DashLine));p.setBrush(Qt.NoBrush)
                p.drawLine(QPointF(left,yy),QPointF(area.right(),yy))
                identity=row.get('broker_order_id') or row.get('position_id') or row.get('id','')
                if index<5:p.drawText(QRectF(area.left()+5,area.top()+22+index*17,area.width()-10,17),Qt.AlignLeft,row['category']+' '+str(identity)+' · '+str(row['entry_price'])+' · '+str(stamp or 'observation time unknown'))
            except (ValueError,KeyError,TypeError):continue
        quote_tags=[]
        for quote in self.quote_lines():
            yy=y(quote['price'])
            if not area.top()<=yy<=area.bottom():continue
            color=self.display[quote['side']+'_color']
            p.setPen(QPen(QColor(color),1,Qt.DashLine));p.drawLine(QPointF(area.left(),yy),QPointF(area.right(),yy))
            quote_tags.append((yy,quote['price'],color,quote['side'][0].upper()))
        # Close means the last visible completed candle, never a made-up live price.
        last=y(rows[-1]['close'])
        if self.display['show_close']:
            p.setPen(QPen(QColor(self.display['close_color']),1,Qt.DotLine));p.drawLine(QPointF(area.left(),last),QPointF(area.right(),last))

        self._paint_ruler(p)
        if self.crosshair and self.mouse and area.contains(self.mouse):
            p.setPen(QPen(QColor(self.display['crosshair_color']),self.display['crosshair_width'],self._pen_style(self.display['crosshair_style'])));p.drawLine(QPointF(self.mouse.x(),area.top()),QPointF(self.mouse.x(),area.bottom()));p.drawLine(QPointF(area.left(),self.mouse.y()),QPointF(area.right(),self.mouse.y()))
        p.restore()
        legend_x=area.right()-165*len(self.studies)-8
        for name,color in (('SMA 20',self.display['sma_color']),('EMA 50',self.display['ema_color'])):
            if name not in self.studies or not self.display['show_study_legend']:continue
            series=self._study_values.get(name,[]);index=len(self.bars)-self.offset-1
            value=series[index] if 0<=index<len(series) else None
            text=name+(' '+f'{value:.{self.precision}f}' if value is not None else ' · warming up')
            p.setPen(QColor(color));p.drawText(QRectF(max(12,legend_x),2,160,22),Qt.AlignRight|Qt.AlignVCenter,text);legend_x+=165

        if self.volume:
            volumes=[]
            for row in rows:
                try:volumes.append(max(0,float(row['tick_volume'])) if row.get('tick_volume') is not None else None)
                except (ValueError,TypeError):volumes.append(None)
            maximum=max((v for v in volumes if v is not None),default=0)
            known=any(v is not None for v in volumes)
            p.setPen(QColor(self.display['foreground']));p.drawText(14,int(area.bottom()+16),f'Tick volume · not exchange volume · max {maximum:,.0f} ticks' if known else 'Tick volume unavailable for this source')
            if maximum:
                for i,v in enumerate(volumes):
                    if v is None:continue
                    color=QColor(self.display['volume_bull_color'] if float(rows[i]['close'])>=float(rows[i]['open']) else self.display['volume_bear_color']);color.setAlpha(105)
                    height=max(12,self.display['volume_height']-28);p.fillRect(QRectF(start+i*step,self.time_axis_rect().top()-4-v/maximum*height,max(1,step*.65),v/maximum*height),color)
        self._paint_axes(p)
        self._paint_projection_captions(p)


