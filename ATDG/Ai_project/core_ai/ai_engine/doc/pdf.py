import re
import logging
from datetime import datetime
from core_ai.ai_engine.doc.doc_generator import DocumentationGenerator
from core_ai.mongo_utils import get_mongo_db
from bson import ObjectId


logger = logging.getLogger(__name__)

class PDFGenerator(DocumentationGenerator):

    def _get_original_filename_from_analysis_id(self, analysis_id):
     db = None
     try:
        db = get_mongo_db()
        if not db: return None

        try:
            query_id = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
        except Exception:
            return None

        result = db.analysis_results.find_one({"_id": query_id})
        
        code_file_id = result.get('code_file_id') if result else None
        
        if code_file_id:
            try:
                file_query_id = ObjectId(str(code_file_id)) if ObjectId.is_valid(str(code_file_id)) else code_file_id
                code_file = db.code_files.find_one({"_id": file_query_id})
                if code_file:
                    return code_file.get('filename')
            except Exception as e:
                logger.error(f"Error fetching code file: {e}")

        return None
     except Exception as e:
        logger.error(f"Error in database lookup: {e}")
        return None
    

    def _format_output(self, content, data):

        content_str = str(content) if content else ""
        image_url = data.get('image_url', '')
        analysis_id = data.get('analysis_id', 'unknown')

        filename = "Analysis Report"
        filename_match = re.search(r'File[:\s]+([^\s\n]+)', content_str)
        if filename_match:
            filename = filename_match.group(1).strip()
        else:
            db_filename = self._get_original_filename_from_analysis_id(analysis_id)
            if db_filename: filename = db_filename
        
        safe_filename = filename.replace('<', '&lt;').replace('>', '&gt;')

        generation_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        main_content_html = self._convert_text_to_enhanced_html(content_str)
        
        full_html = f"""
        <html>
        <head>
            <style>
                @page {{
                    size: A4;
                    margin: 2cm;
                    @bottom-right {{ content: "Page " counter(page) " of " counter(pages); font-size: 8pt; color: #95a5a6; }}
                }}
                body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: #2d3436; line-height: 1.6;direction: ltr; }}
                .header-centered {{
                      text-align: center;
                      width: 100%;
                      padding: 50px 0 30px 0;
                      border: none; /* إزالة الخط السفلي */

                      }}
                .header {{ text-align: center; border-bottom: 3px solid #5a3d9a; padding-bottom: 15px; margin-bottom: 25px;  }}
                .logo {{ color: #5a3d9a; font-size: 32pt; font-weight: bold;margin-bottom: 10px; }}
                .logo-accent {{ color: #8e44ad; }}
                .project-title {{ font-size: 18pt; color: #2d3436; margin-top: 5px; }}
                /* تحسينات النصوص */
                p {{ margin-bottom: 12px; text-align: justify; word-wrap: break-word; }}
                h2, h3 {{ page-break-after: avoid; }}
                ul {{ margin: 10px 0; padding-left: 20px; }}
                li {{ margin-bottom: 5px; }}

                .standard-section {{
                      background: transparent; 
                      padding: 10px 0;
                      margin-bottom: 15px;
                      border: none;
                        }}

                /* تنسيق الكود الذي طلبته (Inline Code) */
                code {{ 
                    background: #f1f2f6; 
                    color: #2c3e50; 
                    padding: 2px 5px; 
                    border-radius: 3px; 
                    font-family: 'Courier New', monospace; 
                    font-size: 95%; 
                }}
                /* بطاقة الكلاس - متوافقة مع تقسيمات البرومبت */
                .class-card {{
                   background: transparent;
                   border: none;
                    padding: 0;
                     margin-top: 25px;
                }}
                 /* تنسيق الكلاسات */
                .class-header {{
                   background: #fcfcfc;
                   padding : 10px 20px; 
                   border-left: 6px solid #5a3d9a;
                   display: inline-block;
                   border-radius: 0 10px 10px 0;
                   margin-bottom: 15px;
                   font-size: 18pt;
                   color: #2d3436;
                }}

                .detail-key {{
                    color: #2980b9;
                    font-weight: bold;
                    text-transform: uppercase;
                    font-size: 9pt;
                    display: block;
                    margin-top: 12px;
                    border-left: 3px solid #3498db;
                    padding-left: 8px;
                    background: #f1f7ff;
                }}

                .source-code {{ 
                    background: #f8f9fa; 
                    color: #2c3e50; 
                    padding: 20px; 
                    border-radius: 5px; 
                    font-family: 'Courier New', monospace; 
                    font-size: 8pt; 
                    line-height: 1.4; 
                    border: 1px solid #dee2e6; 
                    white-space: pre-wrap; 
                    word-wrap: break-word; /* تحسين: لمنع خروج الكود عن الصفحة */
                    max-height: 450px; 
                    overflow: hidden; 
                }}
        
                /* كود */
                code {{ background: #f1f2f6; color: #2c3e50; padding: 2px 5px; border-radius: 3px; font-family: 'Courier New', monospace; font-size: 95%; }}

                /* عنوان القسم في الـ High Level */
                .high-level-section {{
                            color: #2c3e50;
                            font-size: 18pt;
                            border-bottom: 2px solid #3498db;
                            padding-bottom: 8px;
                            margin-top: 35px;
                    }}

                /* عنوان الميثود - تمييز لوني واضح */
                .method-title {{
                        color: #8e44ad;
                       padding: 10px 15px;
                       font-size: 13pt;
                        margin: 0;
                    }}

                .method-container {{
                        border: 1px solid #ffdada; 
                       border-left: 5px solid #e74c3c; 
                        border-radius: 8px;
                            margin-top: 20px 0;
                         background: #fff5f5;
                         page-break-inside: avoid;
                           }}
                .method-description-area {{
                               padding: 10px 0 10px 20px; /* إزاحة لليمين ليعطي شكلاً شجرياً */
                                  background: transparent;
                               border: none;
                                 }}     
                /* إعادة تنسيق القوائم لتبدو احترافية */
                .method-description-area ul {{
                       margin: 5px 0;
                     padding-left: 20px;
                     list-style-type: square; /* شكل المربعات للقوائم */
                     }}

                .class-content-wrapper {{
                     margin-left: 40px; /* إزاحة محتوى الكلاس بالكامل لليمين */
                      border-left: 2px dashed #dcdde1; /* خط منقط يربط العناصر كشجرة */
                    padding-left: 20px;
                }}

                .method-description-area li {{
                     margin-bottom: 6px;
                    color: #34495e;
                      }}

                .relation-tag {{
                       background: #eef2ff;
                      color: #3f51b5;
                      padding: 2px 8px;
                      border-radius: 12px; /* يجعلها تشبه الكبسولة */
                      font-size: 8.5pt;
                      font-weight: bold;
                      text-transform: uppercase;
                      display: inline-block;
                              }}

                .footer {{ position: fixed; bottom: -1cm; width: 100%; text-align: center; font-size: 8pt; color: #95a5a6; border-top: 1px solid #eee; padding-top: 5px; }}
            </style>
        </head>
        <body>
            <div class="header-centered">
                <div class="logo">&lt;/&gt; Docs<span class="logo-accent">Gen</span></div>
                <div style="color: #636e72; font-size: 8pt; text-transform: uppercase; letter-spacing: 2px;">
                    Technical Intelligence Report
                </div>
                <div class="project-title">{safe_filename}</div>
                <div style="font-size: 9pt; color: #b2bec3;">Generated on: {generation_date}</div>
            </div>

            {f'<div style="text-align:center;margin-bottom: 20px;"><h3>Architecture Visualization</h3><img src="{image_url}" style="width:100%; border: 1px solid #ddd; border-radius: 10px;"></div>' if image_url else ''}

            <div class="content">
                {main_content_html}
            </div>

            {f'''
            <div class="code-section" style="page-break-before: always;">
                <h3></i> Source Code Analysis</h3>
                <h4> {safe_filename}</h4>
                <div class="code-content">
                    <pre class="source-code">{data.get('code_content', '').replace('<', '&lt;').replace('>', '&gt;')[:10000]}</pre>
                </div>
                {f'<p class="code-note">Note: Showing first 10000 characters of the source code.</p>' if len(data.get('code_content', '')) > 10000 else ''}
            </div>
            ''' if data and data.get('code_content') else ''}

            <div class="footer">
                AutoTest & DocGen   <pdf:pagenumber/>
            </div>
        </body>
        </html>
        """
        return full_html


    def _convert_text_to_enhanced_html(self, content):
     content = re.sub(r'^File[:\s]+.*?\n', '', content, flags=re.MULTILINE)
     sections = re.split(r'(?=## Class:)', content)
     html_output = ""
    
     for section in sections:
        if not section.strip(): continue
        
        if section.startswith('## Class:'):
            section = re.sub(r'## Class:\s*(.+)', r'<h2 class="class-header">Class: \1</h2><div class="class-content-wrapper">', section)
            
            method_sections = re.split(r'(?=### Method:)', section)
            formatted_section = method_sections[0]
            
            for i in range(1, len(method_sections)):
                m_sec = method_sections[i]
                m_sec = re.sub(r'### Method:\s*(.+)', 
                               r'<div class="method-container"><h3 class="method-title">Method: \1</h3><div class="method-description-area">', m_sec)
                formatted_section += m_sec + "</div></div>"
            
            section = formatted_section + "</div>"
        else:
            section = re.sub(r'^##\s+(.+)$', r'<h2 class="high-level-section">\1</h2>', section, flags=re.MULTILINE)

        relations = ['Composition', 'Inheritance', 'Aggregation', 'Association']
        for rel in relations:
            section = re.sub(rf'\b{rel}\b', rf'<span class="relation-tag">{rel}</span>', section)

        keys = ['Purpose', 'Logic Flow', 'Parameters', 'Returns', 'Description', 'Key Capabilities',
                'Executive Summary', 'Main Components', 'Patterns', 'Purpose & Responsibility']
        for key in keys:
            pattern = rf'\*\*{re.escape(key)}\s*\*\*[:\s]*|\*\*{re.escape(key)}[:\s]*\*\*'
            section = re.sub(pattern, rf'<span class="detail-key">{key}</span>', section)

        section = re.sub(r'^\s*-\s+(.+)$', r'<li>\1</li>', section, flags=re.MULTILINE)
        section = re.sub(r'(<li>.*?</li>)+', r'<ul>\g<0></ul>', section, flags=re.DOTALL)

        
        html_output += section

     return html_output