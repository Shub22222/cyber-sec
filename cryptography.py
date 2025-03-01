import tkinter as tk
from tkinter import filedialog, messagebox , Toplevel, Button, Label, PhotoImage
from PIL import Image, ImageTk
from cryptography.fernet import Fernet
import ctypes
import os
import webbrowser 
import win32clipboard
from io import BytesIO

# DPI awareness to improve clarity on high-resolution screens
ctypes.windll.shcore.SetProcessDpiAwareness(1)

# Global variables
image_path = ""
key_path = "secret.key"
image_preview = None  # Image preview holder

# Generate encryption key
def generate_key():
    key = Fernet.generate_key()
    with open(key_path, "wb") as key_file:
        key_file.write(key)
    return key

# Load encryption key
def load_key():
    if not os.path.exists(key_path):
        messagebox.showerror("Error", "Key file not found! Hide a message first.")
        return None
    with open(key_path, "rb") as key_file:
        return key_file.read()

# Encrypt message
def encrypt_message(message, key):
    return Fernet(key).encrypt(message.encode())

# Decrypt message
def decrypt_message(encrypted_message, key):
    return Fernet(key).decrypt(encrypted_message).decode()

def copy_image_to_clipboard():
    global image_path
    if not image_path:
        messagebox.showwarning("Warning", "Please select an image first.")
        return

    try:
        img = Image.open(image_path)

        # Convert to BMP format required for clipboard (DIB without file header)
        output = BytesIO()
        img.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]  # Skip BMP header
        output.close()

        # Set image data into clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

        messagebox.showinfo("Success", "Image copied to clipboard!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to copy image.\n\n{e}")


# Hide message in image
def hide_message_in_image():
    global image_path
    message = message_entry.get("1.0", tk.END).strip()

    if not image_path or not message:
        messagebox.showwarning("Warning", "Please select an image and enter a message.")
        return

    key = generate_key()
    encrypted_message = encrypt_message(message, key)

    img = Image.open(image_path)
    pixels = img.load()

    message_length = len(encrypted_message)

    if img.size[0] * img.size[1] < message_length * 8 + 32:
        messagebox.showerror("Error", "Image too small for this message!")
        return

    for i in range(32):
        pixel = list(pixels[i % img.width, i // img.width])
        pixel[0] = (pixel[0] & ~1) | ((message_length >> (31 - i)) & 1)
        pixels[i % img.width, i // img.width] = tuple(pixel)

    bit_index = 0
    for i in range(32, 32 + message_length * 8):
        pixel = list(pixels[i % img.width, i // img.width])
        byte_index = bit_index // 8
        bit = (encrypted_message[byte_index] >> (7 - (bit_index % 8))) & 1
        pixel[0] = (pixel[0] & ~1) | bit
        pixels[i % img.width, i // img.width] = tuple(pixel)
        bit_index += 1

    output_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
    if output_path:
        img.save(output_path)
        messagebox.showinfo("Success", f"Message hidden & saved to {output_path}\nKey saved as 'secret.key'.")
    else:
        messagebox.showwarning("Warning", "No file selected. Operation cancelled.")

# Extract message from image
def extract_message_from_image():
    global image_path
    if not image_path:
        messagebox.showwarning("Warning", "Please select an image.")
        return

    key = load_key()
    if not key:
        return

    img = Image.open(image_path)
    pixels = img.load()

    message_length = 0
    for i in range(32):
        message_length = (message_length << 1) | (pixels[i % img.width, i // img.width][0] & 1)

    encrypted_message = bytearray()
    for i in range(32, 32 + message_length * 8):
        if len(encrypted_message) <= i // 8 - 4:
            encrypted_message.append(0)
        encrypted_message[i // 8 - 4] = (encrypted_message[i // 8 - 4] << 1) | (pixels[i % img.width, i // img.width][0] & 1)

    try:
        message = decrypt_message(bytes(encrypted_message), key)
        messagebox.showinfo("Success", f"Extracted message:\n\n{message}")
    except Exception as e:
        messagebox.showerror("Error", f"Decryption failed!\n\n{e}")

# Select image and show preview
def select_image():
    global image_path, image_preview
    image_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
    if image_path:
        image_label.config(text=f"Selected: {os.path.basename(image_path)}")
        img = Image.open(image_path).resize((150, 150), Image.Resampling.LANCZOS)
        image_preview = ImageTk.PhotoImage(img)
        preview_label.config(image=image_preview)
        
    else:
        image_label.config(text="No image selected")
        preview_label.config(image="")

# Reset all inputs
def refresh():
    global image_path, image_preview
    image_path = ""
    message_entry.delete("1.0", tk.END)
    image_label.config(text="No image selected")
    preview_label.config(image="")
    preview_label.image = None

# Open share options
def show_share_options():
    if not image_path:
        messagebox.showwarning("Warning", "Please select an image to share.")
        return

    share_window = tk.Toplevel(root)
    share_window.title("Share Image")
    share_window.geometry("400x500")
    

    def open_url(url):
        webbrowser.open(url)
    
    icons = [
        ("Email", "icons/email.png", "https://mail.google.com/"),
        ("WhatsApp", "icons/whatsapp.png", "https://web.whatsapp.com/"),
        ("Facebook", "icons/facebook.png", "https://www.facebook.com/"),
        ("Instagram", "icons/instagram.png", "https://www.instagram.com/"),
        ("X (Twitter)", "icons/twitter.png", "https://twitter.com/"),
        ("Reddit", "icons/reddit.png", "https://www.reddit.com/")
        
    ]

    Label(share_window, text="Share your image to:", font=("Arial", 12, "bold")).pack(pady=10)

    for name, icon_path, url in icons:
        img = PhotoImage(file=icon_path).subsample(10, 10)  # Resize icon if needed
        btn = Button(share_window, text=name, image=img, compound="left", command=lambda u=url: open_url(u), bd=0,padx=10)
        
        btn.image = img  # Keep reference to prevent garbage collection
        btn.pack(pady=5, padx=20, anchor="w")  # Align to left for better look

    

# GUI Setup
root = tk.Tk()
root.title("Steganography Tool")
root.geometry("500x500")

tk.Button(root, text="Select Image", command=select_image).pack(pady=5)
image_label = tk.Label(root, text="No image selected")
image_label.pack()

preview_label = tk.Label(root)
preview_label.pack(pady=5)
copy_button = tk.Button(root, text="📋 Copy Image", command=copy_image_to_clipboard, bg="lightgrey")
copy_button.pack(pady=5)



tk.Label(root, text="Message to Hide:").pack()
message_entry = tk.Text(root, height=5, width=50)
message_entry.pack()

tk.Button(root, text="Hide Message", command=hide_message_in_image, bg="lightgreen").pack(pady=5)
tk.Button(root, text="Extract Message", command=extract_message_from_image, bg="lightblue").pack(pady=5)
tk.Button(root, text="Refresh", command=refresh, bg="lightcoral").pack(pady=5)

tk.Button(root, text="Share", command=show_share_options, bg="orange").pack(pady=10)


root.mainloop()
