"""Read-only painting of source/frame-bound public strategy geometry."""
from PySide6.QtCore import Qt,QPointF,QRectF
from PySide6.QtGui import QColor,QPen,QPainterPath
from sfm_fx_new_age.contracts.domain import instant


class PublicStrategyPaintMixin:
    def public_strategy_layers(self):
        """Only the chart's exact identity and declared source frame; no aliases."""
        if len(self.data_identity or ())!=4 or not self.strategy_layers:return []
        cutoff=instant(self._bounds[1][-1]['close_time']) if self._bounds and self.offset else None
        return [layer for layer in self.strategy_layers
            if (layer['scope_id'],layer['source_epoch'],layer['symbol'],layer['timeframe'])==self.data_identity
            and layer['timeframe'] in self.display['projection_frames']
            and (cutoff is None or instant(layer['available_at'])<=cutoff)]

    def public_strategy_legend_rect(self):
        if self.display['projection_captions']=='Side rail':return None # Summary lives in the external control bar.
        if not self._bounds or not self.display['show_research'] or not self.public_strategy_layers():return None
        area=self.plot_rect();height=self.axis_metrics().height()+6
        return QRectF(area.left()+7,area.bottom()-height-2,max(1,area.width()-14),height)

    def public_strategy_caption_text(self):
        layers=self.visible_public_strategy_layers();counts=self.projection_badge_counts();focus=next((v['name'] for v in layers if v['strategy_id']==self.projection_focus),'All selected')
        return 'Public projections ('+str(len(layers))+'/'+str(len(self.public_strategy_layers()))+') · captions '+str(counts['shown'])+'/'+str(counts['eligible'])+' · '+focus+' · Projection details for all values'

    def visible_public_strategy_layers(self):
        layers=self.public_strategy_layers()
        return [v for v in layers if v['strategy_id']==self.projection_focus] if self.projection_focus else layers

    def public_strategy_geometry(self):
        if not self._bounds or not self.display['show_research'] or not self.data_identity:return []
        area,rows,step,low,high,start=self._bounds;result=[]
        def y(price):return area.bottom()-(float(price)-low)/(high-low)*area.height()
        for layer in self.visible_public_strategy_layers():
            if layer['state'] not in {'READY','NO_SETUP'}:continue
            # A selected as-of snapshot cannot leak a later evaluation into panned older history.
            cutoff=instant(rows[-1]['close_time']) if self.offset else None
            if cutoff and instant(layer['available_at'])>cutoff:continue
            for s in layer['series']:
                points=[]
                for p in s['points']:
                    if cutoff and instant(p['available_at'])>cutoff:continue
                    x=self.known_x(p['time'])
                    if instant(p['time'])<instant(rows[0]['open_time']):continue
                    points.append((x,y(p['price'])))
                if points:result.append(('series',layer,s,points))
            for z in layer['zones']:
                if z.get('state') not in {'CONFIRMED','TOUCHED'}:continue
                if cutoff and instant(z['available_at'])>cutoff:continue
                left=max(area.left(),self.known_x(z['available_at']));height=max(1,y(z['low'])-y(z['high']))
                if left<area.right():result.append(('zone',layer,z,QRectF(left,y(z['high']),area.right()-left,height)))
            for m in layer['markers']:
                stamp=max(m['time'],m['available_at'],key=instant)
                if cutoff and instant(stamp)>cutoff:continue
                if instant(stamp)<instant(rows[0]['open_time']):continue
                x=self.known_x(stamp);yy=y(m['price'])
                if area.left()<=x<=area.right() and area.top()<=yy<=area.bottom():result.append(('marker',layer,m,QPointF(x,yy)))
        return result
    def public_strategy_badge_entries(self):
        rows=[]
        for kind,layer,row,shape in self.public_strategy_geometry():
            if kind=='series':continue
            if kind=='zone':
                band=float(row['low'])!=float(row['high'])
                values=[(shape.top(),float(row['high']),row['label']+(' high' if band else ''))]
                if band:
                    area,_,_,low,high,_=self._bounds
                    bottom=area.bottom()-(float(row['low'])-low)/(high-low)*area.height()
                    values.append((bottom,float(row['low']),row['label']+' low'))
            else:values=[(shape.y(),float(row['price']),row['label'])]
            for yy,price,label in values:
                rows.append((yy,price,self.display['research_color'],label+' · '+layer['name']))
        return rows
    def _paint_public_strategies(self,p):
        geometry=self.public_strategy_geometry();area=self.plot_rect()
        for kind,layer,row,shape in geometry:
            colour=QColor(self.display['research_color'])
            if kind=='series':
                p.setPen(QPen(colour,1.2,Qt.DashLine));p.setBrush(Qt.NoBrush);path=QPainterPath()
                for i,(x,y) in enumerate(shape):
                    if i:path.lineTo(x,y)
                    else:path.moveTo(x,y)
                p.drawPath(path)
            elif kind=='zone':
                colour.setAlpha(18);p.fillRect(shape,colour);colour.setAlpha(140);p.setPen(QPen(colour,1,Qt.DotLine));p.setBrush(Qt.NoBrush);p.drawRect(shape)

            else:
                side=row['side'];p.setPen(QPen(colour,1.4));p.setBrush(colour);x,y=shape.x(),shape.y()
                if side=='NEUTRAL':p.drawEllipse(QPointF(x,y),3.5,3.5)
                else:
                    sign=1 if side=='BUY' else -1
                    path=QPainterPath(QPointF(x,y));path.lineTo(x-4,y+sign*7);path.lineTo(x+4,y+sign*7);path.closeSubpath();p.drawPath(path)
        # Captions share the chart's monotonic research/setup/scenario price rail.
        rect=self.public_strategy_legend_rect()
        if rect:
            text=self.public_strategy_caption_text();background=QColor(self.display['background']);background.setAlpha(235);p.fillRect(rect,background)
            p.setPen(QColor(self.display['research_color']));p.drawText(rect,Qt.AlignLeft|Qt.AlignVCenter,p.fontMetrics().elidedText(text,Qt.ElideRight,int(rect.width())))
        p.setBrush(Qt.NoBrush)
