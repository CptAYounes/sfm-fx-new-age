"""Display-only caption paging and focus. No calculations, source edits or commands."""
import math
from PySide6.QtCore import Qt,QRectF,QPointF
from PySide6.QtGui import QColor,QPen
from .chart_axis import price_badges


class ProjectionCaptionMixin:
    def set_projection_focus(self,key):
        if key is not None and type(key) is not str:raise ValueError('Strategy identity must be a string')
        if key is not None and key not in {v['strategy_id'] for v in self.public_strategy_layers()}:
            raise ValueError('Select an available strategy in this exact chart source')
        self.projection_focus=key;self.projection_page=0;self.update();self.projectionDisplayChanged.emit()

    def reconcile_projection_focus(self):
        if self.projection_focus and self.projection_focus not in {v['strategy_id'] for v in self.public_strategy_layers()}:
            self.projection_focus=None;self.projection_page=0;self.projectionDisplayChanged.emit()

    def set_projection_page(self,page):
        if type(page) is not int:raise ValueError('Whole caption page required')
        pages=self.projection_caption_status()['pages']
        self.projection_page=max(0,min(max(0,pages-1),page));self.update();self.projectionDisplayChanged.emit()

    def projection_rail_width(self):
        if self.display['projection_captions']!='Side rail' or not self.bars:return 0
        public=self.display['show_research'] and any(v['zones'] or v['markers'] for v in self.visible_public_strategy_layers() if v['state'] in {'READY','NO_SETUP'})
        present=public or (self.display['show_research'] and bool(self.levels)) or (self.display['show_setups'] and bool(self.setup_projections)) or (self.display['show_scenarios'] and bool(self.scenario_projection))
        if not present:return 0
        # Always leave at least 180 display pixels for observed candles. If a
        # very small canvas cannot hold a readable rail, disclose 0/N captions.
        available=self.width()-self.price_axis_width()-194
        sample=f"{float(self.bars[-1]['close']):.{self.precision}f}"
        minimum=max(120,self.axis_metrics().horizontalAdvance(sample)+44)
        return min(360,max(minimum,self.width()*.30),available) if available>=minimum else 0

    def projection_caption_rect(self):
        area=self.plot_rect();mode=self.display['projection_captions']
        if mode=='Hidden':return None
        if mode=='Side rail':
            if not self.projection_rail_width():return None
            left=self.price_axis_rect().right()+4
            return QRectF(left,area.top()+4,max(1,self.width()-left-6),max(1,area.height()-8))
        top,bottom=area.top()+4,area.bottom()-4;width=min(590,area.width()-24);left=area.right()-width-12
        legend=self.public_strategy_legend_rect()
        if legend:bottom=min(bottom,legend.top()-4)
        card=self.ruler_card_rect()
        if card and card.right()>left:
            if card.center().y()<area.center().y():top=max(top,card.bottom()+4)
            else:bottom=min(bottom,card.top()-4)
        return QRectF(left,top,max(1,width),max(0,bottom-top))

    def _caption_page_items(self):
        if not self._bounds:return [],0,0,0
        area=self.plot_rect();height=math.ceil(self.axis_metrics().height())+6
        candidates=[v for v in self._projection_badge_entries() if area.top()<=v[0]<=area.bottom()]
        # Prefer proximity to the last visible *completed* close, not a claimed
        # live executable price or an arbitrary highest-price truncation.
        close=float(self._bounds[1][-1]['close'])
        candidates=sorted(enumerate(candidates),key=lambda v:(abs(v[1][1]-close),v[0]))
        rect=self.projection_caption_rect();capacity=int((rect.height()+2)//(height+2)) if rect and rect.height()>=height else 0
        total=len(candidates);pages=math.ceil(total/capacity) if capacity else 0;page=max(0,min(self.projection_page,max(0,pages-1)))
        return [v for _,v in candidates[page*capacity:(page+1)*capacity]],total,pages,page

    def projection_badges(self):
        items,_,_,_=self._caption_page_items();rect=self.projection_caption_rect()
        if not rect or not items:return []
        area=self.plot_rect();height=math.ceil(self.axis_metrics().height())+6
        return price_badges(items,rect.top(),rect.bottom(),self.precision,label_height=height,coalesce=False,anchor_range=(area.top(),area.bottom()))

    def projection_badge_counts(self):
        _,total,_,_=self._caption_page_items();return dict(shown=len(self.projection_badges()),eligible=total)

    def projection_caption_status(self):
        _,total,pages,page=self._caption_page_items();shown=len(self.projection_badges())
        capacity=math.ceil(total/pages) if pages else 0
        rect=self.projection_caption_rect();height=math.ceil(self.axis_metrics().height())+6
        if rect:capacity=int((rect.height()+2)//(height+2))
        return dict(shown=shown,eligible=total,page=page,pages=pages,start=page*capacity+1 if shown else 0,end=page*capacity+shown if shown else 0)

    def projection_badge_layout(self):
        rect=self.projection_caption_rect();metrics=self.axis_metrics();height=math.ceil(metrics.height())+6;result=[]
        if not rect:return result
        for badge in self.projection_badges():
            box=QRectF(rect.left(),badge['label_y'],rect.width(),height)
            price_text=f"{badge['price']:.{self.precision}f}";price_width=metrics.horizontalAdvance(price_text)+12
            price_rect=QRectF(box.right()-price_width,box.top(),price_width-4,box.height())
            label_rect=QRectF(box.left()+5,box.top(),max(1,box.width()-price_width-12),box.height())
            result.append(dict(badge,rect=box,price_text=price_text,price_rect=price_rect,label_rect=label_rect))
        return result

    def _paint_projection_captions(self,p):
        rect=self.projection_caption_rect()
        if not self._bounds or not rect:return
        p.save();p.setFont(self.axis_font())
        if self.display['projection_captions']=='Side rail':
            p.fillRect(rect.adjusted(-3,-4,4,4),QColor(self.display['axis_background_color']))
            p.setClipRect(rect.adjusted(-3,0,0,0))
        else:p.setClipRect(self.plot_rect())
        for badge in self.projection_badge_layout():
            box=badge['rect'];bg=QColor(self.display['background']);bg.setAlpha(240);p.fillRect(box,bg)
            p.setPen(QPen(QColor(badge['color']),1,Qt.DotLine))
            anchor=QPointF(rect.left()-3,badge['actual_y']) if self.display['projection_captions']=='Side rail' else QPointF(self.plot_rect().right(),badge['actual_y'])
            p.drawLine(anchor,QPointF(box.left() if self.display['projection_captions']=='Side rail' else box.right(),box.center().y()))
            text=p.fontMetrics().elidedText(badge['label'],Qt.ElideRight,int(badge['label_rect'].width()))
            p.drawText(badge['label_rect'],Qt.AlignLeft|Qt.AlignVCenter,text)
            p.drawText(badge['price_rect'],Qt.AlignRight|Qt.AlignVCenter,badge['price_text'])
        p.restore()
