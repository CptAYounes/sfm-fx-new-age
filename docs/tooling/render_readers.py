"""Render canonical companion Markdown to offline HTML and an A4 PDF.

Run with the New Age virtual-environment Python. Uses installed markdown-it-py
and PySide6 only; no network, application launch or source/runtime mutation.
"""
from pathlib import Path
import argparse,datetime,html,json,os,re,sys,textwrap
from urllib.parse import unquote,urlsplit,quote
from markdown_it import MarkdownIt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package',nargs='?',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();root=args.package.resolve();meta=json.loads((root/'package.json').read_text())
    md=MarkdownIt('commonmark',{'html':True}).enable('table')
    paths=['README.md']+[d['path'] for d in meta['documents']]+[d['path'] for d in meta['decisions']]+meta['references']+['diagrams/README.md']
    ids={p:'chapter-'+str(i).zfill(3) for i,p in enumerate(paths)}
    titles={p:next(x.removeprefix('# ').strip() for x in (root/p).read_text().splitlines() if x.startswith('# ')) for p in paths}
    def relocate(rendered,path):
        def fix(m):
            attr,raw=m.group(1),html.unescape(m.group(2));u=urlsplit(raw)
            if u.scheme or u.netloc or raw.startswith('#'):return m.group(0)
            target=(root/path).parent/unquote(u.path)
            target=Path(os.path.normpath(target))
            if target.is_relative_to(root) and str(target.relative_to(root)) in ids:
                val='#'+ids[str(target.relative_to(root))]
            else:
                val=quote(os.path.relpath(target,root),safe='/._-')+('#'+u.fragment if u.fragment else '')
            return attr+'="'+html.escape(val,quote=True)+'"'
        return re.sub(r'(href|src)="([^"]*)"',fix,rendered)
    sections=[];nav=[]
    for p in paths:
        body=relocate(md.render((root/p).read_text()),p)
        sections.append(f'<section class="chapter" id="{ids[p]}" data-title="{html.escape(titles[p],quote=True)}">{body}</section>')
        nav.append(f'<li><a href="#{ids[p]}">{html.escape(titles[p])}</a></li>')
    css='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f6f8fc;color:#162338;font:16px/1.64 system-ui,-apple-system,"DejaVu Sans",sans-serif}aside{position:fixed;inset:0 auto 0 0;width:290px;background:#10213b;color:#edf3ff;overflow:auto;padding:26px 20px}aside h2{font-size:18px;line-height:1.35;margin:0 0 8px}aside small{color:#aabdd8}input{width:100%;padding:11px;margin:18px 0 8px;border:1px solid #607896;border-radius:7px;background:#18304f;color:white}input::placeholder{color:#b6c4d8}nav ul{list-style:none;padding:0}nav li{margin:0 0 6px}nav a{display:block;color:#ccdcf4;text-decoration:none;font-size:12px;padding:5px 4px;border-left:2px solid transparent}nav a:hover,nav a:focus{color:white;border-left-color:#58aaff;background:#1b3657}main{margin-left:290px;padding:36px 4vw;max-width:1550px}.masthead{padding:32px;background:#10213b;color:white;border-radius:12px;margin-bottom:26px}.masthead h1{font-size:30px;line-height:1.2;color:white}.masthead p{color:#c5d5ec}.masthead a{color:#8ec5ff}.chapter{background:white;border:1px solid #dbe3ef;border-radius:10px;padding:34px 38px;margin:0 0 28px;scroll-margin-top:20px;overflow-wrap:anywhere}.chapter h1{font-size:27px;line-height:1.25;border-bottom:3px solid #2f78c7;padding-bottom:15px;color:#142946}.chapter h2{font-size:20px;color:#20466f;margin-top:30px}.chapter h3{font-size:17px;color:#315373}a{color:#165b9f}code{font:12px/1.5 "DejaVu Sans Mono",monospace;background:#edf2f8;padding:2px 4px;border-radius:3px;overflow-wrap:anywhere}pre{padding:18px;background:#edf2f8;border-radius:7px;white-space:pre-wrap;overflow:auto}pre code{padding:0}table{width:100%;border-collapse:collapse;font-size:12px;line-height:1.5;table-layout:auto;margin:16px 0 24px}th{text-align:left;background:#e9f0f9;color:#173b64}td,th{padding:9px 10px;border:1px solid #dce4ef;vertical-align:top;overflow-wrap:anywhere}tr:nth-child(even){background:#f8fafd}img{display:block;max-width:100%;height:auto;margin:20px auto}blockquote{border-left:4px solid #4b86c7;padding-left:16px;color:#496074}.result{font-size:12px;color:#b6c9e6}[hidden]{display:none!important}@media(max-width:950px){aside{position:relative;width:100%;max-height:350px}main{margin-left:0;padding:18px}.chapter{padding:20px}.masthead h1{font-size:25px}table{font-size:10px}}@media print{aside,.masthead{display:none}main{margin:0;padding:0;max-width:none}.chapter{border:0;border-radius:0;padding:0;break-before:page}body{background:white;font-size:10pt}a{color:inherit}h1,h2{break-after:avoid}tr,img{break-inside:avoid}}'''
    script='''const box=document.querySelector('#search');const chapters=[...document.querySelectorAll('.chapter')];const items=[...document.querySelectorAll('nav li')];const cache=chapters.map(s=>s.textContent.toLowerCase());box.addEventListener('input',()=>{const q=box.value.trim().toLowerCase();let n=0;chapters.forEach((s,i)=>{const show=!q||cache[i].includes(q);s.hidden=!show;items[i].hidden=!show;if(show)n++;});document.querySelector('#results').textContent=q?n+' matching chapters':chapters.length+' chapters';});document.querySelectorAll('a[href^="#chapter-"]').forEach(a=>a.addEventListener('click',()=>{const t=document.querySelector(a.getAttribute('href'));if(t)t.hidden=false;}));document.querySelector('#results').textContent=chapters.length+' chapters';'''
    page='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Source-grounded SFM FX New Age architecture and engineering documentation"><title>SFM FX New Age — Engineering Library</title><style>'+css+'</style></head><body><aside><h2>SFM FX New Age<br>Engineering Library</h2><small>Edition 1.0 · 0.2.0 / V23</small><label for="search" style="display:block;font-size:12px;margin-top:16px">Search chapter contents</label><input id="search" type="search" placeholder="Search architecture, Issue, source…"><div class="result" id="results"></div><nav aria-label="Document chapters"><ul>'+''.join(nav)+'</ul></nav></aside><main><header class="masthead"><h1>Architecture and Engineering Library</h1><p>60 main documents · 12 retrospective decisions · 14 reference chapters · 8 diagrams</p><p>Source-grounded design, operational procedures and explicit truth boundaries. Proposed policy is not owner approval; retained qualification is not a fresh market observation.</p><p><a href="SFM_FX_New_Age_Engineering_Handbook.pdf">Open PDF handbook</a> · <a href="README.md">Editable Markdown index</a></p></header>'+''.join(sections)+'</main><script>'+script+'</script></body></html>'
    (root/'SFM_FX_New_Age_Engineering_Handbook.html').write_text(page,encoding='utf-8')

    # PDF uses all primary documents + ADRs. Exhaustive data tables remain in
    # the HTML/Markdown/CSV reference library to keep the print handbook usable.
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QPdfWriter,QTextDocument,QFont,QPainter,QPageSize,QPageLayout,QImage,QColor
    from PySide6.QtCore import QMarginsF,QSizeF,QRectF,Qt,QUrl
    app=QApplication.instance() or QApplication([])
    writer=QPdfWriter(str(root/'SFM_FX_New_Age_Engineering_Handbook.pdf'));writer.setResolution(144)
    writer.setPageSize(QPageSize(QPageSize.A4));writer.setPageMargins(QMarginsF(14,14,14,14),QPageLayout.Millimeter)
    writer.setTitle('SFM FX New Age — Architecture and Engineering Handbook');writer.setCreator('Source-grounded companion documentation renderer')
    width,height=writer.width(),writer.height();footer=48;content_h=height-footer
    printed=[]
    def pdfbody(p):
        raw=(root/p).read_text();rendered=md.render(raw)
        # Use ordinary local hrefs in print; source anchors remain inspectable text.
        rendered=re.sub(r'<a href="[^"]*">(.*?)</a>',r'\1',rendered,flags=re.S)
        # Break long path/hash identifiers inside code to avoid unbounded table cells.
        def wrapcode(m):
            s=m.group(1);s=s.replace('/','/\u200b').replace('_','_\u200b')
            s=re.sub(r'([0-9a-f]{16})(?=[0-9a-f])',lambda match:match.group(1)+'\u200b',s)
            return '<code>'+s+'</code>'
        rendered=re.sub(r'<code>(.*?)</code>',wrapcode,rendered,flags=re.S)
        return rendered
    cover=f'''<h1 style="font-size:34pt;color:#153452">SFM FX New Age</h1><p style="font-size:24pt;color:#315a83">Architecture and<br>Engineering Handbook</p><p style="font-size:13pt">Documentation edition 1.0<br>Source baseline: 0.2.0 / V23 candidate-04<br>{meta['generated_at'][:10]}</p><p>60 complete main documents · 12 retrospective architecture decisions · 8 diagram plates</p><h2>Scope and evidence</h2><p>A companion to the actual local Debian/X11 signal/research platform. Four workspaces, 42 backend identities, 83 analytical methods, six active pairs, four frames and one deliberate human pending Limit Issue edge.</p><p>Fresh documentation checks: 171 offline tests across ten modules, architecture checks and synthetic restart reconciliation. Retained V23 source/installed/native qualification remains historical. No product source, normal state, credentials, user application or broker action was changed.</p><p>Proposed procedures and residual policy choices are explicitly labelled. This handbook is not financial, security, regulatory or profitability certification, and contains no fabricated owner signoff.</p><h2>Using this handbook</h2><p>All main documents and ADRs are printed here. Exhaustive source-derived catalogues, all 83 method/policy definitions, exact test/corpus crosswalks, machine-readable references and editable diagrams are included in the companion HTML/Markdown/CSV library.</p>'''
    printed.append(cover)
    toc='<h1>Contents</h1><h2>Main documents</h2><table>'+''.join('<tr><td>'+html.escape(x['id'])+'</td><td>'+html.escape(x['title'])+'</td></tr>' for x in meta['documents'])+'</table><h2>Architecture decisions</h2><table>'+''.join('<tr><td>'+html.escape(x['id'])+'</td><td>'+html.escape(x['title'])+'</td></tr>' for x in meta['decisions'])+'</table><p>Diagram atlas and reference directory follow the main document set.</p>'
    printed.append(toc)
    for d in meta['documents']:printed.append(pdfbody(d['path']))
    for x in meta['diagrams']:
        printed.append({'diagram':x})
    for d in meta['decisions']:printed.append(pdfbody(d['path']))
    printed.append('<h1>Complete reference directory</h1><p>The offline HTML and editable Markdown include these source-derived appendices. CSV/JSON extracts preserve full records and exact identifiers; source links require the sibling checkout.</p><ul>'+''.join('<li>'+html.escape(titles[p])+' — '+html.escape(p)+'</li>' for p in meta['references'])+'</ul><h2>Validation and preservation</h2><p>Open verification/validation-report.json and verification/source-preservation.json for the checked publication. The checksum manifest binds final package members. It is not a replacement for the product release seal.</p>')
    style='''body{font-family:"DejaVu Sans";font-size:9.5pt;color:#162338}h1{font-size:20pt;color:#173c60;margin-top:0;margin-bottom:13pt}h2{font-size:12.2pt;color:#28577f;margin-top:14pt;margin-bottom:6pt}h3{font-size:10.5pt;color:#28577f}p{margin-top:5pt;margin-bottom:7pt;line-height:125%}li{margin-bottom:4pt}table{border-collapse:collapse;width:100%;font-size:8pt;margin-top:9pt;margin-bottom:10pt}th{background-color:#e4edf8;color:#173c60}td,th{border:1px solid #cdd7e5;padding:5px;vertical-align:top}code{font-family:"DejaVu Sans Mono";font-size:7.8pt;color:#284c70}pre{white-space:pre-wrap;font-size:7.6pt}a{color:#284c70}'''
    def textdoc(part,paged=True):
        doc=QTextDocument();doc.documentLayout().setPaintDevice(writer);doc.setDefaultFont(QFont('DejaVu Sans',10));doc.setDocumentMargin(0)
        doc.setHtml('<html><head><meta charset="utf-8"><style>'+style+'</style></head><body>'+part+'</body></html>')
        if paged:doc.setPageSize(QSizeF(width,content_h))
        else:doc.setTextWidth(writer.width())
        return doc
    # Layout each chapter independently: no invisible next-chapter fragments
    # outside the clip, and chapter page breaks cannot split a diagram image.
    layouts=[part if isinstance(part,dict) else textdoc(part) for part in printed]
    count=sum(1 if isinstance(part,dict) else part.pageCount() for part in layouts)
    painter=QPainter(writer);page_number=0;diagram_rects=[]
    def begin_page(landscape=False):
        nonlocal page_number
        writer.setPageOrientation(QPageLayout.Landscape if landscape else QPageLayout.Portrait)
        if page_number:writer.newPage()
        page_number+=1
    def draw_footer():
        pw,ph=writer.width(),writer.height()
        painter.setPen(QColor('#607088'));painter.setFont(QFont('DejaVu Sans',7.5));painter.drawLine(0,ph-35,pw,ph-35)
        painter.drawText(QRectF(0,ph-30,pw,25),int(Qt.AlignLeft|Qt.AlignVCenter),'SFM FX New Age · Engineering Handbook · Edition 1.0')
        painter.drawText(QRectF(0,ph-30,pw,25),int(Qt.AlignRight|Qt.AlignVCenter),f'{page_number} / {count}')
    for part in layouts:
        if isinstance(part,dict):
            x=part['diagram'];image=QImage(str(root/x['png']));begin_page(image.width()>image.height()*1.5)
            header=textdoc('<h1>Diagram — '+html.escape(x['title'])+'</h1><p>Logical as-built view. See the corresponding design/source document for validation, trust and scope boundaries. Editable Graphviz, SVG and PNG accompany this handbook.</p>',paged=False)
            header.drawContents(painter);top=header.size().height()+24
            pw,ph=writer.width(),writer.height();available_h=ph-footer-top-15
            scale=min((pw-24)/image.width(),available_h/image.height())
            iw,ih=image.width()*scale,image.height()*scale;left=(pw-iw)/2
            rect=QRectF(left,top,iw,ih);painter.drawImage(rect,image)
            assert top+ih<=ph-footer and left>=0 and left+iw<=pw
            diagram_rects.append(dict(id=x['id'],page=page_number,left=left,top=top,width=iw,height=ih,page_width=pw,page_height=ph,fully_inside_content=True))
            draw_footer();continue
        for i in range(part.pageCount()):
            begin_page(False)
            painter.save();painter.setClipRect(QRectF(0,0,width,content_h));painter.translate(0,-i*content_h)
            part.drawContents(painter,QRectF(0,i*content_h,width,content_h));painter.restore();draw_footer()
    painter.end();assert page_number==count
    (root/'verification/pdf-diagram-layout.json').write_text(json.dumps(diagram_rects,indent=2)+'\n')
    result=dict(result='READERS_RENDERED',html_chapters=len(paths),pdf_main_documents=len(meta['documents']),pdf_adrs=len(meta['decisions']),pdf_diagrams=len(meta['diagrams']),pdf_pages=count,pdf_reference_scope='REFERENCE_DIRECTORY_ONLY; exhaustive appendices in HTML/Markdown/CSV',rendered_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (root/'verification/reader-render.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
