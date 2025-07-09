import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
import os
import json
import tempfile
import shutil
from PIL import Image

def compress_image(input_path, output_path, quality=60, max_size=(800, 600)):
    """
    压缩图片以减少文件大小
    
    参数：
    input_path: 输入图片路径
    output_path: 输出图片路径
    quality: JPEG质量 (1-100)
    max_size: 最大尺寸 (width, height)
    """
    try:
        with Image.open(input_path) as img:
            # 转换为RGB模式（如果不是的话）
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 调整尺寸
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 保存为JPEG格式以减少文件大小
            img.save(output_path, 'JPEG', quality=quality, optimize=True)
        return True
    except Exception as e:
        print(f"Error compressing image {input_path}: {e}")
        return False

def send_email_with_embedded_images(sender_email, sender_password, recipient_email, subject, html_body, image_data_list):
    """
    发送带有嵌入图片的HTML邮件
    
    参数：
    sender_email: 发件人邮箱
    sender_password: 发件人邮箱密码
    recipient_email: 收件人邮箱
    subject: 邮件主题
    html_body: HTML邮件内容
    image_data_list: 图片数据列表 [(image_path, content_id), ...]
    """
    
    # 创建邮件对象 - 使用 'related' 以支持嵌入图片
    msg = MIMEMultipart('related')
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    
    # 添加HTML邮件正文
    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)
    
    html_part = MIMEText(html_body, 'html', 'utf-8')
    msg_alternative.attach(html_part)
    
    # 嵌入图片
    for image_path, content_id in image_data_list:
        if os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                img_data = f.read()
                image = MIMEImage(img_data)
                image.add_header('Content-ID', f'<{content_id}>')
                msg.attach(image)
        else:
            print(f"Warning: Image not found: {image_path}")
    
    try:
        # 连接Gmail SMTP服务器
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # 启用TLS加密
        server.login(sender_email, sender_password)
        
        # 发送邮件
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        
        print("邮件发送成功！")
        return True
        
    except Exception as e:
        print(f"邮件发送失败：{e}")
        return False

def send_email_with_attachments(sender_email, sender_password, recipient_email, subject, body, attachment_paths=None):
    """
    发送邮件函数，支持多个附件（保持向后兼容）
    """
    
    # 创建邮件对象
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    
    # 添加邮件正文
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # 如果有附件，添加所有附件
    if attachment_paths:
        for attachment_path in attachment_paths:
            if os.path.exists(attachment_path):
                with open(attachment_path, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {os.path.basename(attachment_path)}',
                )
                msg.attach(part)
            else:
                print(f"Warning: Attachment not found: {attachment_path}")
    
    try:
        # 连接Gmail SMTP服务器
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # 启用TLS加密
        server.login(sender_email, sender_password)
        
        # 发送邮件
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        
        print("邮件发送成功！")
        return True
        
    except Exception as e:
        print(f"邮件发送失败：{e}")
        return False

def send_daily_summary(recipient_email=None, recipient_name=None, test_mode=False):
    """
    发送每日论文摘要邮件，包含论文数量和嵌入式词云图
    
    参数：
    recipient_email: 收件人邮箱，如果为None则使用默认邮箱
    recipient_name: 收件人姓名，用于个性化邮件内容
    test_mode: 如果为True，则只打印信息而不实际发送邮件
    
    返回：
    dict: 包含发送状态信息的字典
    """
    # Configuration
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "ipapers.ai@gmail.com")
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "dqutyjsibzzzgups")
    RECIPIENT_EMAIL = recipient_email or "orrinnj@gmail.com"
    
    if test_mode:
        print(f"TEST MODE: Would send daily summary to {RECIPIENT_EMAIL}")
        if recipient_name:
            print(f"  Recipient name: {recipient_name}")
        return {"success": True, "message": "Test mode - no email sent", "test_mode": True}
    
    # Read daily data
    daily_feed_path = "../../../frontend/public/daily_feed/daily_feed.json"
    
    try:
        with open(daily_feed_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        error_msg = f"Could not find daily feed file at {daily_feed_path}"
        print(f"Error: {error_msg}")
        return {"success": False, "message": error_msg, "error_type": "file_not_found"}
    except json.JSONDecodeError:
        error_msg = "Could not parse daily feed JSON file"
        print(f"Error: {error_msg}")
        return {"success": False, "message": error_msg, "error_type": "json_decode_error"}
    
    # Extract information
    date = data.get('date', 'Unknown')
    total_papers = data.get('total_papers', 0)
    categories = data.get('categories', [])
    
    # Create email subject
    subject = f"{date} Daily Feed ({total_papers} papers)"
    
    # Create HTML email content
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
        }}
        .header {{
            background-color: #667eea;
            color: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }}
        .section {{
            margin: 30px 0;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .category-section {{
            margin: 40px 0;
            padding: 25px;
            background-color: #ffffff;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
        }}
        .category-title {{
            color: #2c3e50;
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 3px solid #3498db;
        }}
        .wordcloud-img {{
            width: 100%;
            max-width: 600px;
            height: auto;
            border-radius: 8px;
            border: 1px solid #ddd;
            margin: 20px 0;
            display: block;
        }}
        .paper-count {{
            background-color: #e74c3c;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            display: inline-block;
            margin-left: 10px;
        }}
        .footer {{
            margin-top: 40px;
            padding: 20px;
            background-color: #2c3e50;
            color: white;
            border-radius: 8px;
            text-align: center;
        }}
        .website-link {{
            text-align: center;
            font-size: 18px;
            margin: 20px 0;
        }}
        .website-link a {{
            color: #3498db;
            text-decoration: none;
            font-weight: bold;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        td {{
            padding: 0;
            vertical-align: top;
        }}
    </style>
</head>
<body>
    <table cellpadding="0" cellspacing="0" width="100%">
        <tr>
            <td>
                <div class="header">
                    <h1>📊 iPapers Daily Feed</h1>
                    <h2>{date}</h2>
                    <p style="font-size: 20px; margin: 0;">Total Papers: <strong>{total_papers}</strong></p>
                </div>

                <div class="section">
                    <h2>🌐 Visit Our Website</h2>
                    <div class="website-link">
                        <a href="https://ipapers.ai/daily-feed">
                            https://ipapers.ai/daily-feed
                        </a>
                    </div>
                </div>

                <div class="section">
                    <h2>🎨 Wordcloud Visualizations</h2>
                </div>
"""
    
    # Create temporary directory to store compressed images
    temp_dir = tempfile.mkdtemp()
    image_data_list = []
    wordcloud_base_path = "../../../frontend/public/daily_feed"
    
    try:
        total_size = 0
        
        # Process each category's word cloud
        for i, category in enumerate(categories):
            display_name = category.get('display_name', 'Unknown')
            paper_count = category.get('paper_count', 0)
            wordcloud_url = category.get('word_cloud_url', '')
            
            if wordcloud_url:
                # Extract filename from URL and build full path
                filename = wordcloud_url.split('/')[-1]
                original_path = os.path.join(wordcloud_base_path, filename)
                
                if os.path.exists(original_path):
                    # Create compressed version of filename
                    compressed_filename = filename.replace('.png', '_compressed.jpg')
                    compressed_path = os.path.join(temp_dir, compressed_filename)
                    
                    # Compress image (slightly larger for online display)
                    if compress_image(original_path, compressed_path, quality=80, max_size=(1200, 900)):
                        file_size = os.path.getsize(compressed_path)
                        total_size += file_size
                        print(f"Compressed {filename}: {file_size / (1024*1024):.1f}MB")
                        
                        # Create unique Content-ID for image
                        content_id = f"wordcloud_{i}"
                        image_data_list.append((compressed_path, content_id))
                        
                        # Add category and image to HTML
                        html_body += f"""
                <div class="category-section">
                    <div class="category-title">
                        {display_name}
                        <span class="paper-count">{paper_count} papers</span>
                    </div>
                    <img src="cid:{content_id}" alt="{display_name} Wordcloud" class="wordcloud-img">
                </div>
"""
                    else:
                        print(f"Failed to compress {filename}, skipping...")
                else:
                    print(f"Original file not found: {original_path}")
        
        # Add email footer
        html_body += """
                <div class="section">
                    <h2>🌐 Visit Our Website</h2>
                    <div class="website-link">
                        <a href="https://ipapers.ai/daily-feed">
                            https://ipapers.ai/daily-feed
                        </a>
                    </div>
                </div>

                <div class="footer">
                    <p>For detailed paper summaries, full abstracts, and in-depth analysis of today's research landscape.</p>
                    <p><em>This is an automated daily summary. For questions or feedback, please contact us.</em></p>
                    <p><strong>iPapers - Your Gateway to Research Discovery</strong></p>
                    <p style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #555;">
                        <a href="https://ipapers.ai/subscription" style="color: #3498db; text-decoration: underline;">
                            Unsubscribe from Daily Feed
                        </a>
                    </p>
                </div>
            </td>
        </tr>
    </table>
</body>
</html>
"""
        
        print(f"Total compressed size: {total_size / (1024*1024):.1f}MB")
        print(f"Preparing to send daily summary for {date}")
        print(f"Total papers: {total_papers}")
        print(f"Categories: {len(categories)}")
        print(f"Embedded images: {len(image_data_list)} (Total size: {total_size / (1024*1024):.1f}MB)")
        
        # Send email
        success = send_email_with_embedded_images(
            SENDER_EMAIL, 
            SENDER_PASSWORD, 
            RECIPIENT_EMAIL, 
            subject, 
            html_body, 
            image_data_list
        )
        
        if success:
            return {
                "success": True, 
                "message": f"Daily summary sent successfully to {RECIPIENT_EMAIL}",
                "recipient_email": RECIPIENT_EMAIL,
                "recipient_name": recipient_name,
                "date": date,
                "total_papers": total_papers,
                "categories_count": len(categories),
                "images_embedded": len(image_data_list)
            }
        else:
            return {
                "success": False, 
                "message": f"Failed to send daily summary to {RECIPIENT_EMAIL}",
                "recipient_email": RECIPIENT_EMAIL,
                "error_type": "email_send_failed"
            }
        
    finally:
        # Clean up temporary files
        try:
            shutil.rmtree(temp_dir)
            print("Temporary files cleaned up")
        except Exception as e:
            print(f"Error cleaning up temporary files: {e}")

# Original send email function (keep backward compatibility)
def send_email(sender_email, sender_password, recipient_email, subject, body, attachment_path=None):
    """
    发送邮件函数
    
    参数：
    sender_email: 发件人邮箱
    sender_password: 发件人邮箱密码（应用专用密码）
    recipient_email: 收件人邮箱
    subject: 邮件主题
    body: 邮件内容
    attachment_path: 附件路径（可选）
    """
    attachment_paths = [attachment_path] if attachment_path else None
    return send_email_with_attachments(sender_email, sender_password, recipient_email, subject, body, attachment_paths)

# Example usage
if __name__ == "__main__":
    # Send daily summary
    result = send_daily_summary()
    
    if result["success"]:
        print("Daily summary sent successfully!")
        print(f"Details: {result['message']}")
    else:
        print("Failed to send daily summary.")
        print(f"Error: {result['message']}")