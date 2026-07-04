import os
import subprocess
from jinja2 import Environment, FileSystemLoader
from src.core.config import config
from src.core.logger import logger

class ResumeGenerator:
    def __init__(self):
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            block_start_string='{%',
            block_end_string='%}',
            variable_start_string='{{',
            variable_end_string='}}',
            comment_start_string='{#',
            comment_end_string='#}',
        )

    def generate_pdf(self, tailored_data: dict, job_id: str):
        template = self.env.get_template('resume_template.tex')
        rendered_tex = template.render(**tailored_data)
        
        tex_file = os.path.join(config.OUTPUT_DIR, f"resume_{job_id}.tex")
        pdf_file = os.path.join(config.OUTPUT_DIR, f"resume_{job_id}.pdf")
        
        with open(tex_file, 'w') as f:
            f.write(rendered_tex)
        
        try:
            # Run pdflatex twice for references if needed, though simple resumes usually need once
            subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', f'-output-directory={config.OUTPUT_DIR}', tex_file],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"Successfully generated PDF: {pdf_file}")
            
            # Cleanup temp files
            for ext in ['.log', '.aux', '.tex']:
                temp_file = os.path.join(config.OUTPUT_DIR, f"resume_{job_id}{ext}")
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
            return pdf_file
        except subprocess.CalledProcessError as e:
            logger.error(f"pdflatex failed: {e.stderr.decode()}")
            return None
        except FileNotFoundError:
            logger.error("pdflatex not found. Please install a TeX distribution.")
            return None
