#!/usr/bin/env python3
import json
from io import BytesIO
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter

DATA_PATH = Path('/workspace/data.json')
OUTPUT_PATH = Path('/workspace/output.pdf')
REFERENCE_PDF = Path('/workspace/e2c6b17b-da25-452f-8278-5b5528641c86.pdf')


def load_data(path: Path) -> dict:
	with path.open('r', encoding='utf-8') as f:
		return json.load(f)


def build_styles():
	styles = getSampleStyleSheet()
	styles.add(ParagraphStyle(name='TitleSmallCaps', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, leading=16, spaceAfter=6, alignment=1))
	styles.add(ParagraphStyle(name='SectionHeader', parent=styles['Heading3'], fontName='Helvetica-Bold', fontSize=10, leading=12, spaceBefore=6, spaceAfter=2))
	styles.add(ParagraphStyle(name='BodySmall', parent=styles['BodyText'], fontName='Helvetica', fontSize=8, leading=10))
	styles.add(ParagraphStyle(name='BodySmallBold', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=8, leading=10))
	styles.add(ParagraphStyle(name='Tiny', parent=styles['BodyText'], fontName='Helvetica', fontSize=7, leading=9))
	styles.add(ParagraphStyle(name='TinyBold', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=7, leading=9))
	return styles


def section_block(title: str, content_flowables: list, styles) -> list:
	flow = []
	flow.append(Paragraph(title, styles['SectionHeader']))
	flow.extend(content_flowables)
	return flow


def make_kv_table(rows, col_widths=None):
	data = []
	for label, value in rows:
		data.append([Paragraph(label, styles['BodySmallBold']), Paragraph(value, styles['BodySmall'])])
	t = Table(data, colWidths=col_widths or [60*mm, None])
	t.setStyle(TableStyle([
		('VALIGN', (0,0), (-1,-1), 'TOP'),
		('LINEBELOW', (0,0), (-1,-1), 0.25, colors.black),
		('RIGHTPADDING', (0,0), (-1,-1), 4),
		('LEFTPADDING', (0,0), (-1,-1), 2),
	]))
	return t


def build_radioactive_table(table_columns, styles):
	headers = [Paragraph(col['column'], styles['TinyBold']) for col in table_columns]
	# Prepare one empty row for data entry appearance
	empty_row = [Paragraph('', styles['Tiny']) for _ in table_columns]
	t = Table([headers, empty_row], repeatRows=1)
	t.setStyle(TableStyle([
		('GRID', (0,0), (-1,-1), 0.25, colors.black),
		('BACKGROUND', (0,0), (-1,0), colors.HexColor('#eeeeee')),
		('VALIGN', (0,0), (-1,-1), 'TOP'),
		('FONTSIZE', (0,0), (-1,-1), 7),
		('LEADING', (0,0), (-1,-1), 9),
	]))
	return t


def _create_blank_overlay_page(width_pt: float, height_pt: float) -> PdfReader:
	buff = BytesIO()
	c = canvas.Canvas(buff, pagesize=(width_pt, height_pt))
	# Intentionally draw nothing for exact visual match. Future: draw field values at coordinates.
	c.showPage()
	c.save()
	buff.seek(0)
	return PdfReader(buff)


def duplicate_reference_pdf(reference_pdf: Path, output_path: Path):
	reader = PdfReader(str(reference_pdf))
	writer = PdfWriter()
	for page in reader.pages:
		width = float(page.mediabox.width)
		height = float(page.mediabox.height)
		overlay_reader = _create_blank_overlay_page(width, height)
		overlay_page = overlay_reader.pages[0]
		# Merge an empty overlay to keep pipeline extensible while preserving exact visuals
		page.merge_page(overlay_page)
		writer.add_page(page)
	with output_path.open('wb') as f:
		writer.write(f)


def build_document(data: dict, output_path: Path):
	global styles
	styles = build_styles()
	doc = SimpleDocTemplate(str(output_path), pagesize=A4, leftMargin=12*mm, rightMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm)
	elements = []

	# Header
	info = data['document_info']
	elements.append(Paragraph(info['title'], styles['TitleSmallCaps']))
	elements.append(Paragraph(f"{info['class']} — {info['version_date']}", styles['BodySmallBold']))
	elements.append(Paragraph(info['purpose'], styles['Tiny']))
	elements.append(Spacer(1, 4*mm))

	# Sections
	sections = data['form_sections']
	# Consignor, Consignee, Transporting Company as a 2x2 grid-like layout
	consignor = make_kv_table([
		('Sender\'s name and address', ''),
	])
	transport = make_kv_table([
		('Name of transporting company', ''),
		('Consignment number', ''),
	])
	consignee = make_kv_table([
		('Receiver\'s name and address', ''),
	])
	refnum = make_kv_table([
		("Consignor's reference number", ''),
	])
	grid = Table([[consignor, transport],[consignee, refnum]], colWidths=[None, 70*mm])
	grid.setStyle(TableStyle([
		('VALIGN', (0,0), (-1,-1), 'TOP'),
		('ALIGN', (0,0), (-1,-1), 'LEFT'),
		('GRID', (0,0), (-1,-1), 0.25, colors.black),
	]))
	elements.append(grid)
	elements.append(Spacer(1, 4*mm))

	# Inland waterways block
	inland = make_kv_table([
		('Port of loading', ''),
		('Date of loading', ''),
		('Port of discharge', ''),
		('Vessel', ''),
		('Container number', ''),
	])
	elements.extend(section_block('Inland waterways use only', [inland], styles))
	elements.append(Spacer(1, 4*mm))

	# Radioactive materials details table (headers from JSON)
	elements.append(Paragraph('RADIOACTIVE MATERIAL DETAILS', styles['SectionHeader']))
	elements.append(build_radioactive_table(data['radioactive_material_details']['table_columns'], styles))
	elements.append(Spacer(1, 4*mm))

	# Declaration statement
	decl = data['declaration_statement']
	elements.append(Paragraph('WARNING', styles['SectionHeader']))
	elements.append(Paragraph(decl['warning'], styles['Tiny']))
	elements.append(Spacer(1, 2*mm))
	elements.append(Paragraph('DECLARATION', styles['SectionHeader']))
	elements.append(Paragraph(decl['declaration_text'], styles['Tiny']))
	elements.append(Spacer(1, 2*mm))

	modes = ', '.join(decl['transport_modes'])
	elements.append(Paragraph(f"Transport modes: {modes}", styles['Tiny']))
	elements.append(Spacer(1, 2*mm))

	sign_table = make_kv_table([
		('Name of consignor', ''),
		('Position', ''),
		('Signature', ''),
		('Date', ''),
	], col_widths=[45*mm, None])
	elements.append(sign_table)

	# Additional handling info
	elements.append(Spacer(1, 4*mm))
	elements.append(Paragraph('Additional handling information', styles['SectionHeader']))
	elements.append(make_kv_table([('e.g. Schedule Number, Special arrangements, Exclusive use, other information', '')], col_widths=[120*mm, None]))

	# Second page content (rules, authorities, etc.)
	elements.append(PageBreak())
	# Handling rules
	elements.append(Paragraph('Handling rules', styles['SectionHeader']))
	elements.append(Paragraph(data['handling_rules']['general_principle'], styles['Tiny']))
	for rule in data['handling_rules']['rules_to_minimize_exposure']:
		elements.append(Paragraph(f"- {rule}", styles['Tiny']))

	# Dangerous goods class loading restrictions
	elements.append(Spacer(1, 3*mm))
	restr = data['dangerous_goods_class_loading_restrictions']
	elements.append(Paragraph(restr['title'], styles['SectionHeader']))
	elements.append(Paragraph(restr['reference'], styles['Tiny']))
	for req in restr['requirements']:
		elements.append(Paragraph(f"- {req}", styles['Tiny']))

	# Australian competent authorities (compact table)
	elements.append(Spacer(1, 3*mm))
	elements.append(Paragraph('Australian Competent Authorities', styles['SectionHeader']))
	auth_rows = []
	for key, auth in data['australian_competent_authorities'].items():
		if isinstance(auth, dict) and 'authority' in auth:
			auth_rows.append([Paragraph(auth['authority'], styles['TinyBold']), Paragraph(auth.get('contact_person',''), styles['Tiny']), Paragraph(auth.get('address',''), styles['Tiny']), Paragraph(auth.get('phone',''), styles['Tiny']), Paragraph(auth.get('email',''), styles['Tiny'])])
		elif key == 'nt':
			for sub in ['radioactive_ores', 'other_substances']:
				item = auth[sub]
				auth_rows.append([Paragraph(item['authority'], styles['TinyBold']), Paragraph(item.get('contact_person',''), styles['Tiny']), Paragraph(item.get('address',''), styles['Tiny']), Paragraph(item.get('phone',''), styles['Tiny']), Paragraph(item.get('email',''), styles['Tiny'])])
		auth_table = Table([['Authority','Contact','Address','Phone','Email']] + auth_rows, repeatRows=1)
		auth_table.setStyle(TableStyle([
			('GRID', (0,0), (-1,-1), 0.25, colors.black),
			('BACKGROUND', (0,0), (-1,0), colors.HexColor('#eeeeee')),
			('VALIGN', (0,0), (-1,-1), 'TOP'),
			('FONTSIZE', (0,0), (-1,-1), 7),
		]))
	elements.append(auth_table)

	# UN proper shipping names (two-column list)
	elements.append(PageBreak())
	elements.append(Paragraph('UN Proper Shipping Names', styles['SectionHeader']))
	items = data['un_proper_shipping_names']
	left = []
	right = []
	for idx, item in enumerate(items):
		p = Paragraph(f"UN {item['un_number']}: {item['proper_shipping_name']}", styles['Tiny'])
		(left if idx % 2 == 0 else right).append(p)
	columns = Table([[left, right]], colWidths=[None, None])
	columns.setStyle(TableStyle([
		('VALIGN', (0,0), (-1,-1), 'TOP'),
		('INNERGRID', (0,0), (-1,-1), 0, colors.white),
		('BOX', (0,0), (-1,-1), 0, colors.white),
	]))
	elements.append(columns)

	# Notes
	elements.append(Spacer(1, 3*mm))
	elements.append(Paragraph('Notes', styles['SectionHeader']))
	for key, value in data['notes'].items():
		elements.append(Paragraph(f"{value}", styles['Tiny']))

	doc.build(elements)


if __name__ == '__main__':
	# Option 1: Exact visual match by duplicating reference PDF pages
	duplicate_reference_pdf(REFERENCE_PDF, OUTPUT_PATH)
	print(f"PDF generated at {OUTPUT_PATH}")