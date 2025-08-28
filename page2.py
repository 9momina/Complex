import json
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.colors import black, white, red
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus.flowables import Flowable
import base64
from io import BytesIO
from PIL import Image
import os

class SinglePageCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        
    def draw_two_column_content(self, data, base64_image_data=None):
        # Page dimensions
        page_width, page_height = A4
        margin = 25
        column_width = (page_width - 3 * margin) / 2
        left_x = margin
        right_x = margin + column_width + margin
        top_y = page_height - margin
        
        # Title
        self.setFont("Helvetica-Bold", 14)
        title_width = self.stringWidth(data['document_info']['title'], "Helvetica-Bold", 14)
        self.drawString((page_width - title_width) / 2, top_y, data['document_info']['title'])
        
        current_y = top_y - 30
        
        # LEFT COLUMN
        left_column = data['left_column']
        y_pos = current_y
        
        # Section 1: Handling Rules
        section1 = left_column['section_1']
        self.setFont("Helvetica-Bold", 9)
        self.drawString(left_x, y_pos, section1['title'])
        y_pos -= 12
        
        # Content
        self.setFont("Helvetica", 7)
        content_lines = self.wrap_text(section1['content'], column_width, 7)
        for line in content_lines:
            self.drawString(left_x, y_pos, line)
            y_pos -= 8
        
        # Subtitle
        self.setFont("Helvetica-Bold", 7)
        self.drawString(left_x, y_pos, section1['subtitle'])
        y_pos -= 10
        
        # Rules
        self.setFont("Helvetica", 6)
        for rule in section1['rules']:
            rule_lines = self.wrap_text(f"• {rule}", column_width - 10, 6)
            for line in rule_lines:
                self.drawString(left_x + 5, y_pos, line)
                y_pos -= 7
        
        y_pos -= 8
        
        # Section 2: Loading Restrictions
        section2 = left_column['section_2']
        self.setFont("Helvetica-Bold", 8)
        title_lines = self.wrap_text(section2['title'], column_width, 8)
        for line in title_lines:
            self.drawString(left_x, y_pos, line)
            y_pos -= 9
        
        self.setFont("Helvetica", 6)
        subtitle_lines = self.wrap_text(section2['subtitle'], column_width, 6)
        for line in subtitle_lines:
            self.drawString(left_x, y_pos, line)
            y_pos -= 7
        
        for restriction in section2['restrictions']:
            rest_lines = self.wrap_text(f"• {restriction}", column_width - 10, 6)
            for line in rest_lines:
                self.drawString(left_x + 5, y_pos, line)
                y_pos -= 7
        
        y_pos -= 8
        
        # Section 3: Table 1 - UN Numbers (WITH VERTICAL LINES)
        section3 = left_column['section_3']
        self.setFont("Helvetica-Bold", 8)
        self.drawString(left_x, y_pos, section3['title'])
        y_pos -= 12
        
        # Draw table with proper formatting matching sample
        table_y = y_pos
        row_height = 10  # Reduced row height to match sample
        col1_width = 35   # UN Number column
        col2_width = column_width - col1_width - 5  # Proper shipping name column
        
        # Headers with black background
        self.setFillColor(colors.black)
        self.rect(left_x, table_y - row_height, col1_width, row_height, fill=1)
        self.rect(left_x + col1_width, table_y - row_height, col2_width, row_height, fill=1)
        
        self.setFillColor(colors.white)
        self.setFont("Helvetica-Bold", 6)
        self.drawString(left_x + 2, table_y - 7, section3['headers'][0])
        self.drawString(left_x + col1_width + 2, table_y - 7, section3['headers'][1])
        
        table_y -= row_height
        
        # Data rows WITH VERTICAL LINES (Table 1 style)
        self.setFont("Helvetica", 5)
        for i, row in enumerate(section3['data']):
            if table_y < 150:  # Leave more space for footer
                break
                
            # White background for all data rows
            self.setFillColor(colors.white)
            self.rect(left_x, table_y - row_height, col1_width, row_height, fill=1, stroke=1)
            self.rect(left_x + col1_width, table_y - row_height, col2_width, row_height, fill=1, stroke=1)
            
            self.setFillColor(colors.black)
            self.drawString(left_x + 2, table_y - 7, row['un_number'])
            
            # Wrap shipping name text
            shipping_lines = self.wrap_text(row['proper_shipping_name'], col2_width - 4, 5)
            self.drawString(left_x + col1_width + 2, table_y - 7, shipping_lines[0] if shipping_lines else "")
            
            table_y -= row_height
        
        # Add footnotes for Table 1
        y_pos = table_y - 10
        self.setFont("Helvetica", 5)
        for footnote in section3.get('footnotes', []):
            footnote_lines = self.wrap_text(footnote, column_width, 5)
            for line in footnote_lines:
                self.drawString(left_x, y_pos, line)
                y_pos -= 6
        
        # RIGHT COLUMN
        right_column = data['right_column']
        y_pos = current_y
        
        # Section 1: In Case of Accident
        r_section1 = right_column['section_1']
        self.setFont("Helvetica-Bold", 9)
        self.drawString(right_x, y_pos, r_section1['title'])
        y_pos -= 12
        
        # Content
        self.setFont("Helvetica", 7)
        content_lines = self.wrap_text(r_section1['content'], column_width, 7)
        for line in content_lines:
            self.drawString(right_x, y_pos, line)
            y_pos -= 8
        
        # Procedures
        self.setFont("Helvetica", 6)
        for procedure in r_section1['procedures']:
            proc_lines = self.wrap_text(f"• {procedure}", column_width - 10, 6)
            for line in proc_lines:
                self.drawString(right_x + 5, y_pos, line)
                y_pos -= 7
        
        # FIXED IMAGE RENDERING
        if base64_image_data:
            try:
                y_pos -= 10
                # Clean the base64 data - remove any whitespace/newlines
                clean_base64 = ''.join(base64_image_data.split())
                
                # Decode base64 image
                image_data = base64.b64decode(clean_base64)
                image = Image.open(BytesIO(image_data))
                
                # Calculate dimensions
                img_width = column_width * 0.8
                aspect_ratio = image.height / image.width
                img_height = img_width * aspect_ratio
                
                # Limit height to reasonable size
                if img_height > 100:
                    img_height = 100
                    img_width = img_height / aspect_ratio
                
                # Save temporary image file with proper format
                temp_img_path = 'photo1756382311.jpg'
                # Convert to RGB if necessary (for JPEG compatibility)
                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB')
                image.save(temp_img_path, 'PNG')
                
                # Draw the actual image
                self.drawImage(temp_img_path, right_x, y_pos - img_height, width=img_width, height=img_height)
                y_pos -= img_height + 10
                
                # Clean up temporary file
                if os.path.exists(temp_img_path):
                    os.remove(temp_img_path)
                
                print(f"Successfully embedded image: {img_width}x{img_height}")
                
            except Exception as e:
                print(f"Error processing image: {e}")
                # Fallback to placeholder
                img_width = column_width * 0.8
                img_height = 60
                self.setStrokeColor(colors.black)
                self.setFillColor(colors.lightgrey)
                self.rect(right_x, y_pos - img_height, img_width, img_height, fill=1)
                self.setFillColor(colors.black)
                self.setFont("Helvetica", 8)
                self.drawString(right_x + 10, y_pos - img_height/2, "Image Load Error")
                y_pos -= img_height + 10
        
        # Section 2: Emergencies
        r_section2 = right_column['section_2']
        self.setFont("Helvetica-Bold", 10)
        self.setFillColor(colors.red)
        self.drawString(right_x, y_pos, "EMERGENCIES")
        y_pos -= 12
        
        self.setFillColor(colors.black)
        self.setFont("Helvetica-Bold", 8)
        emergency_lines = self.wrap_text(r_section2['subtitle'], column_width, 8)
        for line in emergency_lines:
            self.drawString(right_x, y_pos, line)
            y_pos -= 9
        
        self.setFont("Helvetica", 7)
        self.drawString(right_x, y_pos, r_section2['emergency_contact'])
        y_pos -= 15
        
        # Section 3: Table 2 - Australian Competent Authorities (NO VERTICAL LINES - ONLY HORIZONTAL)
        r_section3 = right_column['section_3']
        self.setFont("Helvetica-Bold", 8)
        title_lines = self.wrap_text(r_section3['title'], column_width, 8)
        for line in title_lines:
            self.drawString(right_x, y_pos, line)
            y_pos -= 9
        
        y_pos -= 5
        
        # Draw authorities table with ONLY HORIZONTAL LINES (Table 2 style)
        auth_table_y = y_pos
        auth_row_height = 22  # Row height from previous adjustment
        col1_w = 60   # State/Territory column
        col2_w = 90   # Contact column  
        col3_w = column_width - col1_w - col2_w - 10  # Authority column
        
        # Headers with black background - NO VERTICAL LINES
        self.setFillColor(colors.black)
        # Draw one continuous header rectangle
        self.rect(right_x, auth_table_y - auth_row_height, column_width, auth_row_height, fill=1, stroke=0)
        
        self.setFillColor(colors.white)
        self.setFont("Helvetica-Bold", 6)
        # Center header text vertically in taller row
        header_y_offset = (auth_row_height - 6) / 2 + 2  # Adjusted for better centering
        self.drawString(right_x + 1, auth_table_y - auth_row_height + header_y_offset, r_section3['headers'][0])
        self.drawString(right_x + col1_w + 1, auth_table_y - auth_row_height + header_y_offset, r_section3['headers'][1])
        self.drawString(right_x + col1_w + col2_w + 1, auth_table_y - auth_row_height + header_y_offset, r_section3['headers'][2])
        
        auth_table_y -= auth_row_height
        
        # Data rows with ONLY HORIZONTAL LINES (Table 2 style)
        self.setFont("Helvetica", 4)
        for i, row in enumerate(r_section3['data']):
            # White background for all rows - NO VERTICAL LINES, only horizontal line at bottom
            self.setFillColor(colors.white)
            # Draw one continuous row rectangle with no stroke
            self.rect(right_x, auth_table_y - auth_row_height, column_width, auth_row_height, fill=1, stroke=0)
            
            self.setFillColor(colors.black)
            
            # State/Territory - multiline support
            state_lines = self.wrap_text(row['state_territory'], col1_w - 2, 4)
            line_y = auth_table_y - auth_row_height + 4  # Adjusted for taller row
            for line in state_lines[:3]:  # Max 3 lines
                self.drawString(right_x + 1, line_y, line)
                line_y -= 4
            
            # Contact - multiline support
            contact_lines = self.wrap_text(row['contact'], col2_w - 2, 4)
            line_y = auth_table_y - auth_row_height + 4
            for line in contact_lines[:3]:  # Max 3 lines
                self.drawString(right_x + col1_w + 1, line_y, line)
                line_y -= 4
            
            # Authority - multiline support
            auth_lines = self.wrap_text(row['competent_authority'], col3_w - 2, 4)
            line_y = auth_table_y - auth_row_height + 4
            for line in auth_lines[:3]:  # Max 3 lines
                self.drawString(right_x + col1_w + col2_w + 1, line_y, line)
                line_y -= 4
            
            # Draw horizontal line slightly below the row to avoid text overlap
            self.setStrokeColor(colors.black)
            self.line(right_x, auth_table_y - auth_row_height - 2, right_x + column_width, auth_table_y - auth_row_height - 2)
            
            auth_table_y -= auth_row_height
        
        # Ensure the last horizontal line is drawn if data exists
        if r_section3.get('data'):
            self.setStrokeColor(colors.black)
            self.line(right_x, auth_table_y - auth_row_height - 2, right_x + column_width, auth_table_y - auth_row_height - 2)
    
    def wrap_text(self, text, max_width, font_size):
        """Wrap text to fit within specified width"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            if self.stringWidth(test_line, "Helvetica", font_size) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines

def create_single_page_pdf(json_file_path, base64_file_path, output_pdf_path):
    # Read JSON data
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            full_data = json.load(f)
            data = full_data.get("document", {}).get("page_2", {})
        print(f"Successfully loaded JSON data from {json_file_path}")
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return False
    
    # Read base64 image data if available
    base64_image_data = None
    try:
        with open(base64_file_path, 'r', encoding='utf-8') as f:
            base64_image_data = f.read().strip()
            print(f"Loaded image data: {len(base64_image_data)} characters")
    except Exception as e:
        print(f"Could not load image: {e}")
    
    # Create PDF
    try:
        c = SinglePageCanvas(output_pdf_path, pagesize=A4)
        c.draw_two_column_content(data, base64_image_data)
        c.save()
        print(f"Single-page PDF generated successfully: {output_pdf_path}")
        return True
    except Exception as e:
        print(f"Error creating PDF: {e}")
        return False

if __name__ == "__main__":
    # File paths
    json_file = "data.json"
    base64_file = "image_base64.txt"
    output_pdf = "radioactive_material_table2_fixed.pdf"
    
    # Generate PDF
    success = create_single_page_pdf(json_file, base64_file, output_pdf)
    if success:
        print("PDF generation completed successfully!")
    else:
        print("PDF generation failed!")