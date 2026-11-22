"""Bounded human display preferences. No broker, Qt or analytical authority."""
from copy import deepcopy
import math,re
from .domain import instant

KINDS=('Level','Vertical','Trend','Ray','Rectangle','Ellipse','Triangle','Fibonacci','Text')
FIB_LEVELS=(0.,.236,.382,.5,.618,.786,1.)
OBJECT_STYLE={'name':'','color':'#F4C66B','width':1.4,'line_style':'Solid','fill':True,'opacity':12,
              'show_label':True,'show_prices':True,'extend_left':False,'extend_right':False,
              'text':'Note','font_size':12,'bold':False,'fib_levels':list(FIB_LEVELS),'snap':'Inherit','show_angle':False,
              'fill_color':None,'text_color':None,'label_background':None}
DISPLAY_DEFAULTS={'background':'#101622','foreground':'#DCE5F2','grid_color':'#263248','bull_color':'#5DE1A6',
 'bear_color':'#FF7B88','line_color':'#73C7FF','wick_width':1.15,'candle_width':64,'right_margin':3,
 'price_padding':10,'show_close':True,'show_forming':True,'show_research':True,'show_broker':True,
 'show_setups':True,'show_scenarios':True,'projection_frames':['W1','D1','H4','H1'],'projection_captions':'Side rail',
 'show_labels':True,'snap_mode':'Nearby','snap_distance':8,'one_shot':False,'pan_mode':'Time and price',
 'crosshair_width':1.,'volume_height':58,'drawing_defaults':{},
 'grid_horizontal':True,'grid_vertical':True,'grid_style':'Solid','crosshair_style':'Dash',
 'bull_filled':True,'bear_filled':True,'line_width':1.6,'dot_radius':2.2,
 'show_drawings':True,'show_title':True,'show_study_legend':True,
 'axis_font_size':10,'nudge_pips':1.,'nudge_bars':1,'hit_distance':14,'select_filled':True,
 'axis_panel':True,'axis_minor_ticks':True,'show_axis_highlight':True,
 'price_tick_spacing':48,'time_tick_spacing':115,'time_label_format':'Adaptive UTC',
 'ruler_color':'#F4C66B','show_ruler_card':True,'show_ruler_guides':True,'ruler_position':'Top left',
 'axis_background_color':'#131A27','axis_color':'#DCE5F2','axis_border_color':'#263248',
 'title_color':'#DCE5F2','crosshair_color':'#DCE5F2','selection_color':'#DCE5F2',
 'bull_wick_color':'#5DE1A6','bear_wick_color':'#FF7B88','bull_border_color':'#5DE1A6','bear_border_color':'#FF7B88',
 'bid_color':'#F4C66B','ask_color':'#5DE1A6','close_color':'#73C7FF','forming_color':'#73C7FF',
 'sma_color':'#F4C66B','ema_color':'#BC9FFF','research_color':'#73C7FF','setup_color':'#BC9FFF',
 'scenario_color':'#F4C66B','broker_color':'#5DE1A6','local_order_color':'#BC9FFF',
 'volume_bull_color':'#5DE1A6','volume_bear_color':'#FF7B88'}

# One palette catalogue is shared by preferences and renderer coverage tests.
COLOR_GROUPS=(
 ('Chart / axes',(('background','Chart background'),('foreground','General text'),('title_color','Chart title'),
  ('axis_background_color','Axis rail background'),('axis_color','Axis labels'),('axis_border_color','Axis borders / minor ticks'),
  ('grid_color','Grid'),('crosshair_color','Crosshair / cursor badges'),('selection_color','Object selection / hover'))),
 ('Price / candles',(('bull_color','Bullish candle fill'),('bear_color','Bearish candle fill'),('bull_wick_color','Bullish wick / OHLC'),
  ('bear_wick_color','Bearish wick / OHLC'),('bull_border_color','Bullish candle border'),('bear_border_color','Bearish candle border'),
  ('line_color','Line / dot chart'),('close_color','Completed close line'),('bid_color','Bid line / badge'),('ask_color','Ask line / badge'),('forming_color','Partial forming candle'))),
 ('Studies / volume',(('sma_color','SMA 20'),('ema_color','EMA 50'),('volume_bull_color','Rising tick volume'),('volume_bear_color','Falling tick volume'))),
 ('Projections / measurement',(('research_color','Research zones / labels'),('setup_color','Candidate / signal projections'),
  ('scenario_color','Manual calculator scenario'),('broker_color','Broker order / position display'),('local_order_color','Local order display'),('ruler_color','Measurement / ruler'))))

def color(value):
    if not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value):raise ValueError('RGB colour required')
    return value

def number(value,low,high):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:raise ValueError('Display value outside allowed range')
    return value

def anchor_count(kind):return 1 if kind in {'Level','Vertical','Text'} else 2

def validate_style(values):
    if type(values) is not dict or set(values)-set(OBJECT_STYLE):raise ValueError('Unknown object property')
    result=deepcopy(values)
    for k,v in values.items():
        if k=='color':color(v)
        elif k in {'fill_color','text_color','label_background'}:
            if v is not None:color(v)
        elif k=='width':number(v,.5,6)
        elif k=='opacity':number(v,0,80)
        elif k=='font_size':number(v,8,28)
        elif k in {'fill','show_label','show_prices','extend_left','extend_right','bold','show_angle'}:
            if type(v) is not bool:raise ValueError('Boolean object property required')
        elif k=='line_style' and v not in {'Solid','Dash','Dot','Dash dot'}:raise ValueError('Unsupported line style')
        elif k=='snap' and v not in {'Inherit','Nearby','Always','Off'}:raise ValueError('Unknown object snap mode')
        elif k in {'name','text'}:
            if type(v) is not str or len(v)>(80 if k=='name' else 1024) or '\x00' in v:raise ValueError('Bounded plain text required')
        elif k=='fib_levels':
            if type(v) not in {list,tuple} or not 1<=len(v)<=16:raise ValueError('Use 1–16 unique Fibonacci ratios')
            for x in v:number(x,-5,10)
            if len(set(v))!=len(v):raise ValueError('Fibonacci ratios must be unique')
            result[k]=sorted(v)
    return result

def validate_drawing(obj):
    required={'id','kind','anchors','color','locked','hidden'}
    if type(obj) is not dict or not required<=set(obj) or set(obj)-required-set(OBJECT_STYLE):raise ValueError('Invalid local drawing properties')
    if obj['kind'] not in KINDS or type(obj['id']) is not str or not 1<=len(obj['id'])<=128:raise ValueError('Invalid local drawing identity/type')
    if type(obj['anchors']) not in {list,tuple} or len(obj['anchors'])!=anchor_count(obj['kind']):raise ValueError('Wrong drawing topology')
    for a in obj['anchors']:
        if type(a) not in {list,tuple} or len(a)!=2:raise ValueError('Timestamp/price anchor required')
        instant(a[0]);number(a[1],1e-10,1e10)
    if any(type(obj[k]) is not bool for k in ('locked','hidden')):raise ValueError('Boolean drawing flags required')
    validate_style({k:v for k,v in obj.items() if k in OBJECT_STYLE})
    return deepcopy(obj)

def style_for(obj):return deepcopy(OBJECT_STYLE)|{k:deepcopy(v) for k,v in obj.items() if k in OBJECT_STYLE}

def validate_display(values):
    if type(values) is not dict or set(values)-set(DISPLAY_DEFAULTS):raise ValueError('Unknown chart setting')
    for k,v in values.items():
        if k.endswith('_color') or k in {'background','foreground'}:color(v)
        elif k in {'show_close','show_forming','show_research','show_broker','show_setups','show_scenarios','show_labels','one_shot','grid_horizontal','grid_vertical','bull_filled','bear_filled','show_drawings','show_title','show_study_legend','select_filled','axis_panel','axis_minor_ticks','show_axis_highlight','show_ruler_card','show_ruler_guides'}:
            if type(v) is not bool:raise ValueError('Boolean chart setting required')
        elif k=='projection_frames':
            if type(v) is not list or any(type(f) is not str for f in v) or len(v)!=len(set(v)) or set(v)-{'W1','D1','H4','H1'}:raise ValueError('Unique supported projection timeframes required')
        elif k=='projection_captions':
            if type(v) is not str or v not in {'Side rail','Overlay','Hidden'}:raise ValueError('Unknown projection caption mode')
        elif k=='snap_mode' and v not in {'Nearby','Always','Off'}:raise ValueError('Unknown snap mode')
        elif k=='pan_mode' and v not in {'Time and price','Time only'}:raise ValueError('Unknown pan mode')
        elif k=='time_label_format':
            if v not in {'Adaptive UTC','ISO date + time','Date only'}:raise ValueError('Unknown UTC label format')
        elif k=='ruler_position':
            if v not in {'Top left','Top right','Bottom left','Bottom right'}:raise ValueError('Unknown ruler readout position')
        elif k in {'grid_style','crosshair_style'}:
            if v not in {'Solid','Dash','Dot','Dash dot'}:raise ValueError('Unknown display line style')
        elif k=='drawing_defaults':
            if type(v) is not dict or set(v)-set(KINDS):raise ValueError('Unknown drawing default type')
            for item in v.values():validate_style(item)
        elif k not in {'snap_mode','pan_mode'}:
            lo,hi={'wick_width':(.5,4),'candle_width':(15,90),'right_margin':(0,20),'price_padding':(2,40),
                   'snap_distance':(2,20),'crosshair_width':(.5,3),'volume_height':(35,120),
                   'line_width':(.5,6),'dot_radius':(1,6),'axis_font_size':(8,16),'nudge_pips':(.1,100),'nudge_bars':(1,20),'hit_distance':(4,32),
                   'price_tick_spacing':(28,100),'time_tick_spacing':(70,240)}[k]
            number(v,lo,hi)
            if k=='nudge_bars' and type(v) is not int:raise ValueError('Whole bars required for nudge')
    return deepcopy(values)
