"""Chart gestures and menus. Local drawing edits never publish broker commands."""
from copy import deepcopy
import math
from html import escape
from PySide6.QtCore import Qt,QPointF,QRectF,QTimer,QEvent
from PySide6.QtWidgets import QMenu,QToolTip
from sfm_fx_new_age.contracts.domain import instant
from sfm_fx_new_age.contracts.chart_display import KINDS,style_for
from .chart_object_interactions import ObjectInteractionMixin

class ChartInteractionMixin(ObjectInteractionMixin):
    def event(self,event):
        if event.type()==QEvent.ToolTip:
            for item in self.projection_badge_layout():
                if item['rect'].contains(event.pos()):
                    QToolTip.showText(event.globalPos(),'<qt>'+escape(item['label'])+'<br>Price '+escape(item['price_text'])+' · analytical projection only</qt>',self)
                    return True
            rect=self.public_strategy_legend_rect()
            if rect and rect.contains(event.pos()):
                QToolTip.showText(event.globalPos(),'<qt>'+escape(self.public_strategy_caption_text())+'<br>All values: Layers → Public projection details…</qt>',self)
                return True
        return super().event(event)

    def quote_lines(self):
        q=self._quotes
        if len(self.data_identity or ())!=4 or tuple(q.get(k) for k in ('scope_id','source_epoch','symbol'))!=self.data_identity[:3] or q.get('state') not in {'CURRENT','STALE'}:return []
        try:
            bid,ask=float(q['bid']),float(q['ask'])
            if not (math.isfinite(bid) and math.isfinite(ask) and 0<bid<=ask):return []
        except (KeyError,ValueError,TypeError):return []
        suffix=' · snapshot' if q['state']=='STALE' else ''
        return [dict(side=s,price=v,label=s.title()+suffix) for s,v,on in (('bid',bid,self.show_bid),('ask',ask,self.show_ask)) if on]
    @staticmethod
    def _distance(pos,a,b):
        dx,dy=b.x()-a.x(),b.y()-a.y();length=dx*dx+dy*dy
        ratio=max(0,min(1,((pos.x()-a.x())*dx+(pos.y()-a.y())*dy)/length)) if length else 0
        return math.hypot(pos.x()-a.x()-ratio*dx,pos.y()-a.y()-ratio*dy)
    def _set_option(self,name,value):setattr(self,name,value);self.update();self.optionsChanged.emit()
    def _object_action(self,callback):
        try:callback();self.update()
        except ValueError as exc:self.hovered.emit(str(exc))
    def _request_editor(self,signal,*args):
        # Let QAction dispatch and popup grabs finish before starting a modal.
        QTimer.singleShot(0,self,lambda:signal.emit(*args))
    def populate_object_menu(self,menu):
        selected=self.drawings.get(self.drawings.selected)
        if selected:
            a=menu.addAction('Object settings / colours…',lambda:self._request_editor(self.editDrawing,selected['id']) if len(self.drawings.selection)==1 else self._request_editor(self.editSelection));a.setObjectName('selectedObjectSettings')
            a=menu.addAction('Object properties… (Enter)',lambda:self._request_editor(self.editDrawing,selected['id']));a.setEnabled(len(self.drawings.selection)==1)
            menu.addAction('Style selected objects…',lambda:self._request_editor(self.editSelection))
            menu.addAction('Duplicate selection (Ctrl+Shift+D)',lambda:self._object_action(self.drawings.duplicate))
            menu.addAction('Copy selection (Ctrl+C)',self.copy_objects)
            menu.addAction('Cut selection (Ctrl+X)',lambda:(self.copy_objects(),self.drawings.delete()))
            menu.addAction('Send selection to back',lambda:self.drawings.reorder(self.drawings.selection,False))
            menu.addAction('Bring selection to front',lambda:self.drawings.reorder(self.drawings.selection,True))
            menu.addAction('Unlock selection' if selected['locked'] else 'Lock selection',lambda:self.drawings.modify_many(self.drawings.selection,locked=not selected['locked']))
            menu.addAction('Hide selection',lambda:self.drawings.modify_many(self.drawings.selection,hidden=True))
            menu.addAction('Delete selection (Del)',self.drawings.delete);menu.addSeparator()
        else:
            a=menu.addAction('Select an object on the chart or in Objects');a.setEnabled(False)
        paste=menu.addAction('Paste local objects (Ctrl+V)',self.paste_objects);paste.setEnabled(bool(self._clipboard and self._clipboard[0]==self.data_identity))
        a=menu.addAction('Undo (Ctrl+Z)',self.drawings.undo);a.setEnabled(self.drawings.can_undo)
        a=menu.addAction('Redo (Ctrl+Y)',self.drawings.redo);a.setEnabled(self.drawings.can_redo)
        a=menu.addAction('Local drawings visible (Ctrl+H)');a.setCheckable(True);a.setChecked(self.display['show_drawings'] and not self.drawings.hidden);a.triggered.connect(self._set_option_on_book)
        menu.addAction('Manage objects… (Ctrl+D)',self.manageDrawings.emit)
    def build_context_menu(self):
        menu=QMenu(self);menu.setObjectName('chartContextMenu');settings=menu.addMenu('Settings');settings.setObjectName('chartContextSettings')
        menu.settings_menu=settings # Retain the Python-owned submenu wrapper until popup disposal.
        settings.addAction('Chart colours…',lambda:self._request_editor(self.colourSettingsRequested))
        settings.addAction('Chart settings…',lambda:self._request_editor(self.settingsRequested))
        settings.addAction('Axes / rulers…',lambda:self._request_editor(self.axisSettingsRequested))
        settings.addAction('Object selection…',lambda:self._request_editor(self.selectionSettingsRequested))
        menu.addSeparator();self.populate_object_menu(menu);menu.addSeparator()
        action=menu.addAction('Public projection details…',lambda:self._request_editor(self.publicDetailsRequested));action.setObjectName('publicProjectionDetailsContext');action.setEnabled(bool(self.public_strategy_layers()))
        menu.addAction('Chart settings…',self.settingsRequested.emit);menu.addAction('Latest / follow (End)',self.latest);menu.addAction('Fit chart',self.fit)
        menu.addAction('Auto price scale',lambda:self._set_option('price_range',None))
        styles=menu.addMenu('Chart type')
        for style in ('OHLC','Candles','Line','Dot'):
            a=styles.addAction(style);a.setCheckable(True);a.setChecked(self.style==style);a.triggered.connect(lambda checked,style=style:self._set_option('style',style))
        viewing=menu.addMenu('Viewing options')
        for text,key in (('Grid (Ctrl+G)','grid'),('Crosshair (middle click)','crosshair'),('Tick volume','volume'),('Bid price line (Ctrl+B)','show_bid'),('Ask price line','show_ask')):
            a=viewing.addAction(text);a.setCheckable(True);a.setChecked(getattr(self,key));a.toggled.connect(lambda checked,key=key:self._set_option(key,checked))
        wheel=menu.addMenu('Mouse wheel')
        for mode in ('Zoom','Scroll'):
            a=wheel.addAction(mode+' · Ctrl+wheel always zooms');a.setCheckable(True);a.setChecked(self.wheel_mode==mode);a.triggered.connect(lambda checked,mode=mode:self._set_option('wheel_mode',mode))
        drawings=menu.addMenu('Local drawings')
        for tool in ('Pan','Select','Ruler','Time ruler','Price ruler',*KINDS):
            a=drawings.addAction(tool);a.triggered.connect(lambda checked,tool=tool:(setattr(self,'tool',tool),self.toolChanged.emit(tool)))
        drawings.addSeparator();drawings.addAction('Manage drawings… (Ctrl+D)',self.manageDrawings.emit)
        a=drawings.addAction('Undo (Ctrl+Z)',self.drawings.undo);a.setEnabled(self.drawings.can_undo)
        a=drawings.addAction('Redo (Ctrl+Y)',self.drawings.redo);a.setEnabled(self.drawings.can_redo)
        drawings.addAction('Hide/show all (Ctrl+H)',self._set_option_on_book);drawings.addAction('Clear local drawings',self.drawings.clear)
        menu._submenus=(settings,styles,viewing,wheel,drawings)
        menu._submenu_actions=tuple(child.menuAction() for child in menu._submenus)
        return menu
    def _set_option_on_book(self):self.drawings.hidden=False;self.set_display({'show_drawings':not self.display['show_drawings']})
    def contextMenuEvent(self,event):
        axis=self.axis_at(event.pos())
        if axis:
            menu=QMenu(self);menu.setObjectName('chartAxisMenu')
            tool='Price ruler' if axis=='price' else 'Time ruler'
            menu.addAction('Measure '+axis+' (Shift+drag axis)',lambda:(setattr(self,'tool',tool),self.toolChanged.emit(tool)))
            menu.addAction('Clear measurement (Esc)',self.clear_ruler).setEnabled(self.ruler is not None)
            menu.addSeparator();menu.addAction('Auto price scale' if axis=='price' else 'Reset time zoom',lambda:self._set_option('price_range',None) if axis=='price' else self.zoom(80/self.window))
            menu.addAction('Axis / ruler settings…',self.axisSettingsRequested.emit);menu.addAction('Chart colours…',self.colourSettingsRequested.emit);self._show_context_menu(menu,event.globalPos());return
        hit=self._hit_drawing(event.pos())
        if hit and hit[0]['id'] not in self.drawings.selection:self.drawings.selected=hit[0]['id'];self.update()
        menu=self.build_context_menu();self._show_context_menu(menu,event.globalPos())
    def _show_context_menu(self,menu,position):
        # Nonblocking popups avoid an extra nested exec loop when a colour or
        # object dialog is opened from a menu action. Ownership lasts until hide.
        self._context_menu=menu;menu.aboutToHide.connect(menu.deleteLater);menu.popup(position)
    def wheelEvent(self,event):
        amount=event.angleDelta().y() or event.angleDelta().x()
        if amount:
            if self.wheel_mode=='Zoom' or event.modifiers() & Qt.ControlModifier:self.zoom(.8 if amount>0 else 1.25,event.position())
            else:self.pan(max(1,self.window//12)*(1 if amount>0 else -1))
        event.accept()
    def mousePressEvent(self,event):
        if event.button()==Qt.MiddleButton:self._set_option('crosshair',not self.crosshair);return
        if event.button()!=Qt.LeftButton:return
        self.setFocus();pos=event.position();point=self._point(pos)
        if self._bounds:
            area=self._bounds[0]
            axis=self.axis_at(pos)
            mode={'Ruler':'range','Time ruler':'time','Price ruler':'price'}.get(self.tool)
            if axis and (event.modifiers() & Qt.ShiftModifier or mode):
                self._begin_ruler(pos,axis);return
            if axis=='price':self.drag=('scale',pos.y(),self._bounds[3:5]);return
            if axis=='time':self.drag=('time_scale',pos.x(),self.window);return
            if area.contains(pos) and (mode or self.tool=='Pan' and event.modifiers() & Qt.ShiftModifier):
                self._begin_ruler(pos,mode or 'range');return
        if not self._bounds or not self._bounds[0].contains(pos):return
        if self.tool=='Select':self.drag=('select',pos,pos,bool(event.modifiers() & Qt.ControlModifier),list(self.drawings.selection));self.update();return
        default=self.display['drawing_defaults'].get(self.tool,{})
        anchor=self._anchor(pos,snap=not event.modifiers() & (Qt.AltModifier|Qt.ShiftModifier),mode=default.get('snap'))
        if not anchor:return
        if self.tool in {'Level','Vertical','Text'}:
            try:self._new_object(self.tool,[anchor])
            except ValueError as exc:self.hovered.emit(str(exc))
            return
        if self.tool in KINDS:
            self._draft=dict(id='draft',kind=self.tool,anchors=[anchor,anchor],color='#F4C66B',locked=False,hidden=False,**{k:v for k,v in self.display['drawing_defaults'].get(self.tool,{}).items() if k!='color'})
            self._draft['color']=self.display['drawing_defaults'].get(self.tool,{}).get('color','#F4C66B');self.drag=('draw',pos);return

        hit=self._hit_drawing(pos)
        if hit:
            obj,handle=hit;ctrl=bool(event.modifiers() & Qt.ControlModifier);was=obj['id'] in self.drawings.selection
            if not was:self.drawings.select(obj['id'],additive=ctrl)
            originals={} if obj['locked'] else {i:deepcopy(self.drawings.get(i)['anchors']) for i in self.drawings.selection if not self.drawings.get(i)['locked']}
            self.drag=('object',obj['id'],handle,originals,anchor,pos,ctrl,was,False);self.update();return
        if point:self.inspected.emit(dict(self._bounds[1][point[0]]))
        for level,rect in reversed(self.research_regions() if self.display['show_research'] else []):
            if rect.contains(pos):self.evidenceSelected.emit(level.get('level_id') or level.get('overlay_id'));break
        self.drawings.selected=None;self.drag=('pan',pos.x(),self.offset,pos.y(),self._bounds[3:5])
    def mouseReleaseEvent(self,event):
        drag=self.drag
        if drag and drag[0]=='ruler':self._move_ruler(event.position())
        if drag and drag[0]=='select':
            rect=QRectF(drag[1],event.position()).normalized();ids=[]
            click=(event.position()-drag[1]).manhattanLength()<5
            if click:
                hit=self._hit_drawing(event.position())
                if hit:ids=[hit[0]['id']]
            elif self.display['show_drawings'] and not self.drawings.hidden:
                for obj in self.drawings.items:
                    if obj['hidden']:continue
                    points,segments,_,_=self._shape(obj)
                    if any(rect.contains(p) for p in points) or any(rect.intersects(QRectF(a,b).normalized().adjusted(-1,-1,1,1)) for a,b in segments):ids.append(obj['id'])
            self.drawings._selection=[i for i in drag[4] if i not in ids]+[i for i in ids if i not in drag[4]] if click and drag[3] else list(dict.fromkeys((drag[4] if drag[3] else [])+ids))
        if drag and drag[0]=='draw' and self._draft:
            if (event.position()-drag[1]).manhattanLength()>3:
                try:self._new_object(self._draft['kind'],self._draft['anchors'])
                except ValueError as exc:self.hovered.emit(str(exc))
            self._draft=None
        if drag and drag[0]=='object':
            if self.drawings._gesture is not None:self.drawings.commit()
            elif drag[6] and drag[7]:self.drawings.select(drag[1],additive=True)
        self.drag=None;self._remember();self.update();self.viewChanged.emit()
    def mouseMoveEvent(self,event):
        self.mouse=event.position();pos=event.position()
        if self.drag and self._bounds:
            mode=self.drag[0]
            if mode=='pan':
                self.offset=max(0,min(max(0,len(self.bars)-self.window),self.drag[2]+int((pos.x()-self.drag[1])/self._bounds[2])));self.follow=self.offset==0
                if self.display['pan_mode']=='Time and price' and abs(pos.y()-self.drag[3])>3:
                    low,high=self.drag[4];delta=(pos.y()-self.drag[3])/self._bounds[0].height()*(high-low);self.price_range=(low+delta,high+delta)
                self.viewChanged.emit()
            elif mode=='scale':
                low,high=self.drag[2];middle=(low+high)/2;half=(high-low)/2*math.exp(max(-4,min(4,(pos.y()-self.drag[1])/160)));self.price_range=(middle-half,middle+half)
            elif mode=='time_scale':
                desired=max(8,min(2000,round(self.drag[2]*math.exp(max(-4,min(4,(pos.x()-self.drag[1])/200))))));self.zoom(desired/self.window)
            elif mode=='ruler':self._move_ruler(pos)
            elif mode=='select':self.drag=('select',self.drag[1],pos,self.drag[3],self.drag[4])
            elif mode in {'draw','object'}:
                obj=self.drawings.get(self.drag[1]) if mode=='object' else self._draft
                anchor=self._anchor(pos,snap=not event.modifiers() & (Qt.AltModifier|Qt.ShiftModifier),mode=style_for(obj)['snap'] if obj else None)
                if anchor:
                    if mode=='draw':self._draft['anchors'][1]=anchor
                    elif self.drag[3] and (pos-self.drag[5]).manhattanLength()>3:
                        _,identity,handle,original,first,press,ctrl,was,started=self.drag
                        if not started:
                            self.drawings.begin()
                            if ctrl:
                                try:
                                    copies=self.drawings.duplicate(list(original));original={o['id']:deepcopy(o['anchors']) for o in copies};identity=copies[-1]['id'];handle=None
                                except ValueError as exc:self.drawings.cancel();self.drag=None;self.hovered.emit(str(exc));return
                            self.drag=('object',identity,handle,original,first,press,ctrl,was,True)
                        delta=self._time_index(anchor[0])-self._time_index(first[0]);price_delta=anchor[1]-first[1]
                        proposed={i:([(self._stamp_index(self._time_index(t)+delta),v+price_delta) for t,v in values]) for i,values in original.items()}
                        if handle is not None and len(original)==1:
                            if isinstance(handle,str):proposed[identity]=self._resize_anchors(dict(self.drawings.get(identity),anchors=original[identity]),handle,anchor)
                            else:proposed[identity]=list(original[identity]);proposed[identity][handle]=anchor
                        try:
                            for values in proposed.values():self.drawings.anchors(values)
                            for i,values in proposed.items():self.drawings.move(i,values,remember=False)
                        except ValueError:self.hovered.emit('Movement refused: positive price required')
        point=self._point(pos)
        if point:
            i,price=point;row=self._bounds[1][i];pip=.01 if self.precision==3 else .0001
            text=row['open_time'][:16].replace('T',' ')+' UTC  '+'  '.join(k[0].upper()+' '+str(row[k]) for k in ('open','high','low','close'))
            if row.get('tick_volume') is not None:text+='  V '+str(row['tick_volume'])
            if self.ruler and self.drag and self.drag[0]=='ruler':
                text=self.ruler_readout()['text']
            else:
                index=len(self.bars)-self.offset-len(self._bounds[1])+i
                for name in sorted(self.studies):
                    series=self._study_values.get(name,[]);value=series[index] if index<len(series) else None
                    if value is not None:text+=f'  {name} {value:.{self.precision}f}'
            self.hovered.emit(text)
        elif self.drag and self.drag[0]=='ruler':pass # Axis measurements already emit their exact readout.
        elif self.axis_at(pos):
            axis=self.axis_at(pos);self.hovered.emit(axis.title()+' axis · drag to scale · Shift+drag to measure · right-click for settings')
        elif self.tool!='Pan' or self.drag and self.drag[0]=='object':
            anchor=self._anchor(pos)
            self.hovered.emit(('Local drawing coordinates · '+anchor[0][:19]+' · '+f'{anchor[1]:.{self.precision}f}'+' · no candle observed here') if anchor else 'Outside chart')
        else:self.hovered.emit('No completed candle at cursor')
        axis=self.axis_at(pos)
        hit=self._hit_drawing(pos) if self.tool in {'Pan','Select'} and not self.drag and not axis else None
        self._hover_object=hit[0]['id'] if hit else None
        self.setCursor(Qt.SizeVerCursor if axis=='price' else Qt.SizeHorCursor if axis=='time' else Qt.OpenHandCursor if hit else Qt.CrossCursor if self.tool!='Pan' else Qt.ArrowCursor)
        self.update()
    def leaveEvent(self,event):self.mouse=None;self._hover_object=None;self.update()
    def mouseDoubleClickEvent(self,event):
        axis=self.axis_at(event.position())
        if axis=='price':self.price_range=None;self.update();return
        if axis=='time':self.zoom(80/self.window);return
        hit=self._hit_drawing(event.position())
        if hit:
            self.drawings.cancel();self.drag=None;self.drawings.selected=hit[0]['id'];self.editDrawing.emit(hit[0]['id']);return
        if self._bounds and event.position().x()>self._bounds[0].right():self.price_range=None;self.update()
        else:self.fit()
    def keyPressEvent(self,event):
        key=event.key();ctrl=bool(event.modifiers() & Qt.ControlModifier);alt=bool(event.modifiers() & Qt.AltModifier);shift=bool(event.modifiers() & Qt.ShiftModifier)
        if alt and key in (Qt.Key_Left,Qt.Key_Right,Qt.Key_Up,Qt.Key_Down) and self.drawings.selection:
            n=10 if shift else 1;self.nudge_objects(n if key==Qt.Key_Right else -n if key==Qt.Key_Left else 0,n if key==Qt.Key_Up else -n if key==Qt.Key_Down else 0)
        elif ctrl and key==Qt.Key_C:self.copy_objects()
        elif ctrl and key==Qt.Key_V:self.paste_objects()
        elif ctrl and shift and key==Qt.Key_D:self._object_action(self.drawings.duplicate)
        elif ctrl and key==Qt.Key_X:self.copy_objects();self.drawings.delete()
        elif ctrl and key==Qt.Key_A:self.drawings._selection=[o['id'] for o in self.drawings.items if not o['hidden']];self.update()
        elif alt and key in (Qt.Key_1,Qt.Key_2,Qt.Key_3,Qt.Key_4):self._set_option('style',{Qt.Key_1:'OHLC',Qt.Key_2:'Candles',Qt.Key_3:'Line',Qt.Key_4:'Dot'}[key])
        elif ctrl and shift and key==Qt.Key_Z:self.drawings.redo()
        elif ctrl and key==Qt.Key_Z:self.drawings.undo()
        elif ctrl and key==Qt.Key_Y:self.drawings.redo()
        elif ctrl and key==Qt.Key_H:self._set_option_on_book()
        elif ctrl and key==Qt.Key_D:self.manageDrawings.emit()
        elif ctrl and key==Qt.Key_G:self._set_option('grid',not self.grid)
        elif ctrl and key==Qt.Key_B:self._set_option('show_bid',not self.show_bid)
        elif key==Qt.Key_Delete:self.drawings.delete()
        elif key in (Qt.Key_Return,Qt.Key_Enter) and len(self.drawings.selection)==1:self.editDrawing.emit(self.drawings.selected)
        elif key==Qt.Key_Left:self.pan(2)
        elif key==Qt.Key_Right:self.pan(-2)
        elif key==Qt.Key_PageUp:self.pan(self.window)
        elif key==Qt.Key_PageDown:self.pan(-self.window)
        elif key==Qt.Key_Up:self.periodStepped.emit(-1)
        elif key==Qt.Key_Down:self.periodStepped.emit(1)
        elif key==Qt.Key_Home:self.pan(len(self.bars))
        elif key==Qt.Key_End:self.latest()
        elif key in (Qt.Key_Plus,Qt.Key_Equal):self.zoom(.8)
        elif key==Qt.Key_Minus:self.zoom(1.25)
        elif key==Qt.Key_Escape:
            self.drawings.cancel();self.tool='Pan';self.clear_ruler();self.drag=None;self._draft=None;self.drawings.selected=None;self.toolChanged.emit('Pan');self.update();self.viewChanged.emit()
        else:super().keyPressEvent(event)
