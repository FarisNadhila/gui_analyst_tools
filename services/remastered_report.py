import pandas as pd
import os
from datetime import datetime
import json

def generate_remastered_report(input_file, config, output_folder="output"):
    """
    Generate a consolidated report based on a JSON configuration.
    
    config example:
    {
        "header": "Laporan Media Monitoring\n{client_name}\n{date}\n...",
        "sections": [
            {"type": "Summary/Counts"},
            {"type": "Topic", "groups": [{"name": "Bupati", "keywords": ["..."]}], "other_name": "Lainnya"},
            {"type": "Sentiment", "order": ["Positive", "Neutral", "Negative"]}
        ]
    }
    """
    try:
        if not os.path.exists(input_file):
            return False, f"File tidak ditemukan: {input_file}"
        
        # Read excel
        # Try different sheet names if necessary, default to Sheet1 or the first sheet
        excel_file = pd.ExcelFile(input_file)
        sheet_names = excel_file.sheet_names
        
        # Heuristic: if 'Sheet1' exists, use it. Otherwise use the first sheet.
        # For Pemkab Bogor, it uses 'Pemkab Bogor' and 'Negatif'. 
        # This generic version will assume a single source sheet unless complex logic is needed.
        main_sheet = 'Sheet1' if 'Sheet1' in sheet_names else sheet_names[0]
        df = pd.read_excel(input_file, sheet_name=main_sheet)
        
        # Clean column names
        df.columns = df.columns.astype(str).str.strip()
        
        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)
        
        # Variables for template
        client_name = config.get('client_name', 'Client')
        current_date = datetime.now().strftime("%d %B %Y")
        
        content = []
        
        # 1. Process Header
        header_template = config.get('header', '')
        # Basic placeholder replacement
        header = header_template.replace('{client_name}', client_name).replace('{date}', current_date)
        
        # Summary Counts if needed in header
        if '{summary_counts}' in header or any(f'{{tone_counts_{t}}}' in header for t in ['Positive', 'Neutral', 'Negative']):
            tone_counts = df['Tone'].value_counts() if 'Tone' in df.columns else {}
            header = header.replace('{summary_counts}', 
                f"Positive: {tone_counts.get('Positive', 0)} berita\n"
                f"Neutral: {tone_counts.get('Neutral', 0)} berita\n"
                f"Negative: {tone_counts.get('Negative', 0)} berita"
            )
            for t in ['Positive', 'Neutral', 'Negative']:
                header = header.replace(f'{{tone_counts_{t}}}', str(tone_counts.get(t, 0)))
        
        content.append(header)
        content.append("")
        
        # 2. Process Sections
        for section in config.get('sections', []):
            s_type = section.get('type')
            
            if s_type == "Summary/Counts":
                if 'Tone' in df.columns:
                    tone_counts = df['Tone'].value_counts()
                    content.append("*Ringkasan Isu*")
                    for tone in section.get('order', ['Positive', 'Neutral', 'Negative']):
                        count = tone_counts.get(tone, 0)
                        content.append(f"{tone}: {count} berita")
                    content.append("")

            elif s_type == "Topic":
                if 'Topik' in df.columns and 'Source' in df.columns:
                    # Automatic Grouping by Topic String
                    topic_counts = df['Topik'].value_counts().sort_values(ascending=False)
                    total_articles = len(df)
                    
                    content.append(f"Pemberitaan ({total_articles} artikel)")
                    content.append("")
                    
                    for topic_name, count in topic_counts.items():
                        topic_sources = df[df['Topik'] == topic_name]['Source'].tolist()
                        content.append(f"{topic_name} ({count} artikel)")
                        for i, src in enumerate(topic_sources, 1):
                            content.append(f"{i}. {src}")
                        content.append("")
                else:
                    content.append("Kolom 'Topik' atau 'Source' tidak ditemukan untuk section Topic.")
                    content.append("")

            elif s_type == "Sentiment":
                if 'Tone' in df.columns:
                    order = section.get('order', ['Positive', 'Neutral', 'Negative'])
                    for tone in order:
                        tone_data = df[df['Tone'] == tone]
                        if not tone_data.empty:
                            content.append(f"*{tone}*")
                            content.append("")
                            # Sub-group by Media Type if available
                            if 'Media Type' in df.columns:
                                for m_type in ['media tv', 'media cetak', 'media online']:
                                    m_data = tone_data[tone_data['Media Type'] == m_type]
                                    if not m_data.empty:
                                        content.append(f"*{m_type.title()}*")
                                        # Group by Tier if available
                                        if 'Media Tier' in df.columns:
                                            for tier in [1, 2, 3]:
                                                t_data = m_data[m_data['Media Tier'].astype(str).str.strip() == str(tier)]
                                                if not t_data.empty:
                                                    content.append(f"*Tier {tier}*")
                                                    counter = 1
                                                    for _, row in t_data.iterrows():
                                                        title = row.get('Title', 'No Title')
                                                        media = row.get('Media Name', 'Unknown Media')
                                                        source = row.get('Source', 'No Source')
                                                        content.append(f"{counter}. {media}")
                                                        content.append(f"{title}:")
                                                        content.append(f"{source}")
                                                        content.append("")
                                                        counter += 1
                                        else:
                                            # No tier, just list
                                            counter = 1
                                            for _, row in m_data.iterrows():
                                                title = row.get('Title', 'No Title')
                                                media = row.get('Media Name', 'Unknown Media')
                                                source = row.get('Source', 'No Source')
                                                content.append(f"{counter}. {media}\n{title}:\n{source}\n")
                                                counter += 1
                            else:
                                # No media type, just list by tone
                                counter = 1
                                for _, row in tone_data.iterrows():
                                    title = row.get('Title', 'No Title')
                                    media = row.get('Media Name', 'Unknown Media')
                                    source = row.get('Source', 'No Source')
                                    content.append(f"{counter}. {media}\n{title}:\n{source}\n")
                                    counter += 1
                            content.append("")

            elif s_type == "Media Type":
                if 'Media Type' in df.columns:
                    order = section.get('order', ['media tv', 'media cetak', 'media online'])
                    for m_type in order:
                        m_data = df[df['Media Type'] == m_type]
                        if not m_data.empty:
                            content.append(f"*{m_type.title()}*")
                            # List items
                            counter = 1
                            for _, row in m_data.iterrows():
                                title = row.get('Title', 'No Title')
                                media = row.get('Media Name', 'Unknown Media')
                                source = row.get('Source', 'No Source')
                                content.append(f"{counter}. {media}\n{title}:\n{source}\n")
                                counter += 1
                            content.append("")

        # Save to file
        filename = f"Report_{client_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        output_path = os.path.join(output_folder, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
            
        return True, output_path
        
    except Exception as e:
        import traceback
        return False, f"{str(e)}\n{traceback.format_exc()}"
