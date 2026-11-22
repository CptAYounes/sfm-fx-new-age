"""Study paths must remain stroke-only; no opaque polygons over broker candles."""
from test_chart_workstation import canvas,rows
from sfm_fx_new_age.services.chart_studies import ChartStudyService


def test_line_studies_do_not_fill_the_plot_with_the_last_candle_brush(canvas):
    import math
    _,c=canvas;data=rows()
    for i,row in enumerate(data):
        v=1.1+math.sin(i*.18)*.025
        row.update(open=str(v),high=str(v+.002),low=str(v-.002),close=str(v+.001))
    c.set_data(data,'SYNTHETIC FIXTURE',c.data_identity);c._study_values=ChartStudyService().query(data,('scope',));c.grid=False
    baseline=c.grab().toImage().convertToFormat(__import__('PySide6.QtGui',fromlist=['QImage']).QImage.Format_RGBA8888)
    c.studies={'SMA 20','EMA 50'}
    after=c.grab().toImage().convertToFormat(baseline.format())
    a=bytes(baseline.bits());b=bytes(after.bits())
    changed=sum(a[i:i+4]!=b[i:i+4] for i in range(0,len(a),4))
    assert changed/(baseline.width()*baseline.height())<.06
