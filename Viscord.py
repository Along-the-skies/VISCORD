import time
from tkinter import *
from tkinter import ttk
import random
import sqlite3
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore',category=UserWarning,module='google.cloud')
import threading
import base64
import sounddevice as sd
from scipy.io import wavfile
import os
import winsound




try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None
    print("Warning: paho.mqtt.client is not installed. MQTT features will be disabled.")

from supabase import create_client, client


#===============Emojis===========

emojis= {
    
    ":fire:": "🔥",
    ":heart:": "❤️",
    ":skull:": "💀",
    ":rocket:": "🚀",
    ":wave:": "👋",
    ":smile:": "😄",
    ":laugh:": "😂",
    ":cry:": "😭",
    ":thumbsup:": "👍",
    ":clap:": "👏",
    ":eyes:": "👀",
    ":cool:": "😎",
    ":angry:": "😡",
    ":party:": "🥳",
    ":thinking:": "🤔",
    ":check:": "✅",
    ":cross:": "❌"
}


def convert_emojis(text):
    for code, emoji in emojis.items():
        text = text.replace(code, emoji)
    return text

#========PlaySOUND===============

def Playvoice(filename):
    winsound.PlaySound(filename,winsound.SND_FILENAME)



#==============Supabase DB SETUP ====================== 

SUPABASE_URL = "https://cdivoawflqjorxoufmzo.supabase.co"
SUPABASE_KEY = "sb_publishable_8cAVpH63Mu3revWLRhlOUA_Or-yR175"

db_cloud = None

try:
    db_cloud = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as error:
    print("Warning : Failed to initialize Supabase:", error)
    db_cloud=None

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

#================== DATABASE =================

db = sqlite3.connect("viscord.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_uid TEXT,
    sender TEXT,
    content TEXT,
    msg_date TEXT
)
""")

db.commit()


#==============Date and Time Formatting==============


join_date = datetime.now().strftime("%d %B, %Y")


# ================= PRESENCE SYSTEM =================

users_state = {}
typing_users = {}
typing_indicator = {}
loaded_public_messages = set()

# ================= MQTT =================

SERVER = "test.mosquitto.org"
TOPIC = None


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected Successfully")
    else:
        print("Connection Failed")


def on_message(client, userdata, msg):
    try:
        message = msg.payload.decode("utf-8")
        sender, content = message.split(": ", 1)

        now = time.time()
        current_name = NameEntry.get().strip() if "NameEntry" in globals() else ""

        if content.startswith("PING|"):
            user = content.split("|", 1)[1]
            users_state.setdefault(user, {})
            users_state[user]["last_seen"] = now
            users_state[user]["status"] = "online"
            return

        if content.startswith("TYPING|"):
            user = content.split("|", 1)[1]
            typing_users[user] = now
            typing_indicator[user] = now
            return
        

        if content.startswith("VOICE|"):
            print("Got a voice msg!")

            audio_data = content.split("|", 1)[1]

            filename = f"voice_{int(time.time())}.wav"

            audio_bytes = base64.b64decode(audio_data)

            with open(filename, "wb") as f:
                f.write(audio_bytes)


            my_name = NameEntry.get().strip()
            if my_name == sender:
                add_message("You", f"🎤 Voice Message ({filename})")
            else:
                add_message(sender, f"🎤 Voice Message ({filename})")

            

            Playvoice(filename)

            try:
                os.remove(filename)
                print("Cache Cleared")
            except OSError as e:
                print(f"error :{e.filename} - {e.strerror}")


            return

        if sender == "System":
            if "has joined the server" in content:
                user = content.replace(" has joined the server", "")
                users_state.setdefault(user, {})
                users_state[user]["last_seen"] = now
                users_state[user]["status"] = "online"

            elif "has left the server" in content:
                user = content.replace(" has left the server", "")
                users_state.pop(user, None)

            add_message("System", content)
            return

        users_state.setdefault(sender, {})
        users_state[sender]["last_seen"] = now
        users_state[sender]["status"] = "online"

        msg_date = datetime.now().strftime("%Y-%m-%d")
        room_uid = RoomUIDEntry.get()

        if not "PUBLIC" in TOPIC:
            cursor.execute(
                "INSERT INTO messages (room_uid, sender, content, msg_date) VALUES (?, ?, ?, ?)",
                (room_uid, sender, content, msg_date)
            )
            db.commit()
        elif "PUBLIC" in TOPIC:
            save_public_message("PUBLIC", sender, content, msg_date)

        typing_users.pop(sender, None)
        typing_indicator.pop(sender, None)

        if sender == current_name:
            add_message("You", content)
        else:
            add_message(sender, content)

    except Exception as error:
        print("Failed to parse incoming message:", error)


#================== PUBLIC MESSAGE LOGGING ==================

def save_public_message(room_uid, sender, content, msg_date):
    if db_cloud is None:
        return
    
    try:
        db_cloud.table("public_messages").insert({
            "room_uid": room_uid,
            "sender": sender,
            "content": content,
            "msg_date": msg_date,
            "timestamp": time.time()
        })
    except Exception as error:
        print("Warning: failed to save public message:", error)





#================== MQTT CLIENT SETUP =================

client = None
if mqtt is not None:
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(SERVER, 1883, 60)
        client.loop_start()
    except Exception as error:
        print("Warning: failed to connect MQTT:", error)
        client = None

#=================Public Chat BAckup ==================


def load_public_messages():
    if db_cloud is None:
        return

    try:
        global loaded_public_messages
        loaded_public_messages.clear()  
        last_date = None
        
        current_name = NameEntry.get().strip() if "NameEntry" in globals() else ""
        
        # Query your Supabase table and order the messages properly
        response = (
            db_cloud.table("public_messages")
            .select("*")
            .eq("room_uid", "PUBLIC")
            .order("msg_date", desc=False)
            .order("timestamp", desc=False)
            .execute()
        )
        
        for data in response.data:
            doc_id = str(data.get("id"))
            
            if doc_id not in loaded_public_messages:
                sender = data.get("sender", "Unknown")
                content = data.get("content", "")
                msg_date = data.get("msg_date", "")

                if msg_date != last_date:
                    today = datetime.now().strftime("%Y-%m-%d")
                    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

                    if msg_date == today:
                        label = "Today"
                    elif msg_date == yesterday:
                        label = "Yesterday"
                    else:
                        try:
                            label = datetime.strptime(msg_date, "%Y-%m-%d").strftime("%d %B, %Y")
                        except Exception:
                            label = msg_date

                    add_message("date", f"──────── {label} ────────")
                    last_date = msg_date

                if sender == current_name:
                    add_message("You", content)
                elif sender == "System":
                    add_message("System", content)
                else:
                    add_message(sender, content)

                loaded_public_messages.add(doc_id)
            
    except Exception as error:
        print("Warning: failed to load public messages:", error)





# ================= CLEANUP =================

def update_user_status():
    now = time.time()

    for user in list(users_state.keys()):
        diff = now - users_state[user].get("last_seen", 0)

        if diff > 12:
            users_state.pop(user, None)
        elif diff > 5:
            users_state[user]["status"] = "idle"
        else:
            users_state[user]["status"] = "online"

    if "chat_window" in globals() and chat_window.winfo_exists():
        chat_window.after(1000, update_user_status)


def clean_typing():
    now = time.time()

    for user in list(typing_users.keys()):
        if now - typing_users[user] > 2:
            typing_users.pop(user, None)

    if "chat_window" in globals() and chat_window.winfo_exists():
        chat_window.after(1000, clean_typing)


# ================= COLORS =================

BG = "#1E1F22"
SECONDARY = "#2B2D31"
ACCENT = "#5865F2"
TEXT = "#FFFFFF"
ENTRY = "#383A40"


# ================= LOGIN =================

login = Tk()
login.title("Viscord")
login.geometry("350x350")
login.config(bg=BG)
login.resizable(False, False)

Title = Label(login, text="VISCORD", bg=BG, fg=ACCENT, font=("Arial", 28, "bold"))
Title.pack(pady=20)

NameLabel = Label(login, text="Username", bg=BG, fg=TEXT, font=("Arial", 11))
NameLabel.pack()

NameEntry = Entry(login, bg=ENTRY, fg=TEXT, insertbackground="white",
                  relief=FLAT, font=("Arial", 12))
NameEntry.pack(pady=5, ipadx=50, ipady=8)

RoomLabel = Label(login, text="Server", bg=BG, fg=TEXT, font=("Arial", 11))
RoomLabel.pack(pady=(10, 0))

RoomList = ttk.Combobox(login, state="readonly", font=("Arial", 11))
RoomList["values"] = ("Public", "Server 1", "Server 2", "Server 3")
RoomList.current(1)
RoomList.pack(pady=5)
RoomList.bind("<<ComboboxSelected>>", lambda e: toggle_server_mode())

RoomUIDLabel = Label(login, text="Server UID", bg=BG, fg=TEXT, font=("Arial", 11))
RoomUIDLabel.pack(pady=(10, 0))

RoomUIDEntry = Entry(login, bg=ENTRY, fg=TEXT, insertbackground="white",
                     relief=FLAT, font=("Arial", 12))
RoomUIDEntry.pack(pady=5)

RoomUIDRANDOMButton = Button(
    login,
    text="↻",
    command=lambda: RoomUIDEntry.delete(0, END) or RoomUIDEntry.insert(
        0, ''.join(random.choices(LETTERS, k=6))
    ),
    bg=ACCENT,
    fg="white",
    activebackground="#4752C4",
    activeforeground="white",
    relief=FLAT,
    font=("Arial", 11),
    cursor="hand2",
    width=5
)
RoomUIDRANDOMButton.place(x=280, y=255)


def toggle_server_mode():


    selected= RoomList.get()
    if selected == "Public":
        RoomUIDEntry.delete(0, END)
        RoomUIDEntry.pack_forget()
        RoomUIDEntry.insert(0, "PUBLIC")
        RoomUIDLabel.pack_forget()

        RoomUIDRANDOMButton.place_forget()
    else:
        RoomUIDLabel.pack(pady=(10, 0))
        RoomUIDEntry.pack(pady=5)
        RoomUIDEntry.delete(0, END)

        RoomUIDRANDOMButton.place(x=280, y=255)
        LoginButton.pack_forget()
        LoginButton.pack(pady=20)

def RecordVoice():

    import io
    import numpy as np

    record_window = Toplevel(chat_window)
    record_window.title("Recording")
    record_window.geometry("250x150")
    record_window.config(bg=BG)
    record_window.resizable(False, False)

    Label(
        record_window,
        text="🎤 Recording...",
        bg=BG,
        fg=TEXT,
        font=("Arial", 14, "bold")
    ).pack(pady=10)

    timer_label = Label(
        record_window,
        text="00:00",
        bg=BG,
        fg=ACCENT,
        font=("Arial", 18)
    )
    timer_label.pack()

    recording = True
    start_time = time.time()
    audio_chunks = []
    fs = 16000

    def update_timer():
        if recording:
            elapsed = int(time.time() - start_time)

            minutes = elapsed // 60
            seconds = elapsed % 60

            timer_label.config(
                text=f"{minutes:02}:{seconds:02}"
            )

            record_window.after(1000, update_timer)

    def audio_callback(indata, frames, time_info, status):
        if recording:
            audio_chunks.append(indata.copy())

    stream = sd.InputStream(
        samplerate=fs,
        channels=1,
        dtype="int16",
        callback=audio_callback
    )

    def start_recording():
        stream.start()

    threading.Thread(
        target=start_recording,
        daemon=True
    ).start()

    def StopRecording():
        nonlocal recording

        recording = False

        try:
            stream.stop()
            stream.close()
        except:
            pass

        if len(audio_chunks) == 0:
            record_window.destroy()
            return

        audio_data = np.concatenate(audio_chunks, axis=0)

        buffer = io.BytesIO()

        wavfile.write(
            buffer,
            fs,
            audio_data
        )

        encoded = base64.b64encode(
            buffer.getvalue()
        ).decode()

        print("Voice note recorded!")
        print(encoded)
        

        name = NameEntry.get().strip() # SEND THROUGH MQTT
        client.publish(
             TOPIC,
             f"{name}: VOICE|{encoded}"
         )
        print("BASE64 published")

        record_window.destroy()

    Button(
        record_window,
        text="⏹ Stop",
        command=StopRecording,
        bg="#E74C3C",
        fg="white",
        relief=FLAT,
        font=("Arial", 11, "bold")
    ).pack(pady=15)

    update_timer()


# ================= MESSAGE =================

message_list = None


def add_message(sender, content):
    global message_list
    if message_list is None:
        return
    
    if not message_list or not message_list.winfo_exists():
        return

    message_list.config(state=NORMAL)

    if sender == "You":
        message_list.insert(END, f"You: {content}\n\n", "right")
    elif sender == "System":
        message_list.insert(END, content + "\n\n", "system")
    elif sender == "date":
        message_list.insert(END, content + "\n\n", "date")
    else:
        message_list.insert(END, f"{sender}: {content}\n\n", "left")

    message_list.config(state=DISABLED)
    message_list.see(END)


# ================= CHAT =================

def CHAT(Name, uid):
    global message_list, chat_window
    global Usersbox

    chat_window = Toplevel()
    chat_window.title(f"Viscord - {Name}")
    chat_window.geometry("650x600")
    chat_window.config(bg=BG)

    # ================= SIDEBAR =================
    Usersbox = Frame(
        chat_window,
        bg=SECONDARY,
        width=150,
        height=600,
        highlightbackground="#1A1B1E",
        highlightthickness=2
    )
    Usersbox.pack(side=LEFT, fill=Y)
    Usersbox.pack_propagate(False)

    Label(
        Usersbox,
        text="Users",
        bg=SECONDARY,
        fg=TEXT,
        font=("Arial", 12, "bold")
    ).pack(pady=10)

    UsersList = Listbox(
        Usersbox,
        bg=SECONDARY,
        fg=TEXT,
        relief=FLAT,
        highlightthickness=0,
        font=("Arial", 14)

    )
    UsersList.pack(fill=BOTH, expand=True, padx=5, pady=5)

    # ================= MAIN AREA =================
    MainArea = Frame(
        chat_window,
        bg=BG,
        width=500,
        height=600,
        highlightbackground="#1A1B1E",
        highlightthickness=2
    )
    MainArea.pack(side=RIGHT, fill=BOTH, expand=True)
    MainArea.pack_propagate(False)

    topbar = Frame(MainArea, bg=SECONDARY, height=60)
    topbar.pack(fill=X)

    Label(topbar, text=f"Welcome, {Name}", bg=SECONDARY, fg=TEXT,
          font=("Arial", 15, "bold")).place(x=15, y=15)

    ServerInfoLabel = Label(
        topbar,
        text=f"Server: {RoomList.get()} \nUID: {uid}",
        bg=SECONDARY,
        fg=TEXT,
        font=("Arial", 11)
    )
    ServerInfoLabel.place(x=260, y=15)

    OnlineUsersLabel = Label(
        topbar,
        text="Online: 0",
        bg=SECONDARY,
        fg=TEXT,
        font=("Arial", 9)
    )
    OnlineUsersLabel.place(x=180, y=25)

    # ================= LOGOUT (RESTORED) =================
    def Logout():
        global TOPIC

        if client is not None and TOPIC:
            try:
                client.publish(TOPIC, f"System: {Name} has left the server")
                client.unsubscribe(TOPIC)
            except Exception:
                pass

        TOPIC = None
        chat_window.destroy()
        login.deiconify()

    LogoutButton = Button(
        topbar,
        text="Logout",
        command=Logout,
        bg="#101114",
        fg="white",
        activebackground="#4752C4",
        activeforeground="white",
        relief=FLAT,
        font=("Arial", 11),
        cursor="hand2",
        width=10
    )
    LogoutButton.place(x=400, y=15, width=80, height=30)

    # ================= UI UPDATES =================
    def update_ui():
        OnlineUsersLabel.config(text=f"Online: {len(users_state)}")

        UsersList.delete(0, END)
        for user in users_state:
            if user in typing_users:
                UsersList.insert(END, f"{user} (typing...)")
            else:
                UsersList.insert(END, user)

        if chat_window.winfo_exists():
            chat_window.after(1000, update_ui)

        

    update_ui()
    update_user_status()
    clean_typing()

    def heartbeat():
        if client is not None and TOPIC:
            try:
                client.publish(TOPIC, f"System: PING|{Name}")
            except Exception:
                pass
        chat_window.after(1000, heartbeat)

    heartbeat()

    # ================= CHAT AREA =================
    ChatFrame = Frame(MainArea, bg=BG)
    ChatFrame.pack(fill=BOTH, expand=False)
    ChatFrame.pack_propagate(False)
    ChatFrame.config(height=450)

    scrollbar = Scrollbar(ChatFrame)
    scrollbar.pack(side=RIGHT, fill=Y)

    message_list = Text(
        ChatFrame,
        bg=SECONDARY,
        fg=TEXT,
        wrap=WORD,
        relief=FLAT,
        font=("Arial", 11),
        padx=10,
        pady=10,
        yscrollcommand=scrollbar.set
    )
    message_list.pack(fill=BOTH, expand=True)
    scrollbar.config(command=message_list.yview)

    message_list.tag_configure("left", justify="left", foreground="white")
    message_list.tag_configure("right", justify="right", foreground="#8BE9FD")
    message_list.tag_configure("system", justify="center", foreground="yellow")
    message_list.tag_configure("date", justify="center", foreground="#6C6C6C", font=("Arial", 10, "italic"))
    message_list.config(state=DISABLED)

    if uid == "PUBLIC":
        load_public_messages()
        

    BottomBar = Frame(MainArea, bg=SECONDARY, height=70)
    BottomBar.pack(fill=X, side=BOTTOM)

    MessageEntry = Entry(BottomBar, bg=ENTRY, fg=TEXT)
    MessageEntry.place(x=10, y=15, width=370, height=40)

    def SendMessage():
        msg = MessageEntry.get().strip()
        msg = convert_emojis(msg)
        if msg and TOPIC and client is not None:
            try:
                client.publish(TOPIC, f"{Name}: {msg}")
            except Exception:
                pass
            MessageEntry.delete(0, END)

    def typing(event=None):
        if client is not None and TOPIC:
            try:
                client.publish(TOPIC, f"System: TYPING|{Name}")
            except Exception:
                pass

    MessageEntry.bind("<Key>", typing)
    MessageEntry.bind("<Return>", lambda e: SendMessage())

    Button(
        BottomBar,
        text="Send",
        command=SendMessage,
        bg=ACCENT,
        fg="white",
        relief=FLAT,
        font=("Arial", 11, "bold")
    ).place(x=390, y=15, width=45, height=40)

    Button(
        BottomBar,
        text="  🎙️",
        justify="center",
        
        command=RecordVoice,
        bg=ACCENT,
        fg="white",
        relief=FLAT,
        padx=-5,
        pady=0,
        font=('Ariel',16)
        

    ).place(x=450,y=15,width=30,height=40)

        


    last_date = None

    if uid != "PUBLIC":
        cursor.execute(
            "SELECT sender, content, msg_date FROM messages WHERE room_uid=? ORDER BY id",
            (uid,)
        )

        for sender, content, msg_date in cursor.fetchall():
            if msg_date != last_date:

                today = datetime.now().strftime("%Y-%m-%d")
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

                if msg_date == today:
                    label = "Today"

                elif msg_date == yesterday:
                    label = "Yesterday"

                else:
                    pretty_date = datetime.strptime(msg_date, "%Y-%m-%d").strftime("%d %B, %Y")
                    label = pretty_date

                add_message(
                    "date",
                    f"──────── {label} ────────"
                )

                last_date = msg_date

            if sender == Name:
                add_message("You", content)

            elif sender == "System":
                add_message("System", content)

            else:
                add_message(sender, content)


# ================= CONNECT =================

def Connect():
    global TOPIC

    Name = NameEntry.get().strip()
    uid = RoomUIDEntry.get().strip()

    users_state[Name] = {
    "last_seen": time.time(),
    "status": "online"
    }


    selected = RoomList.get()


    if not Name:
        return
    

    if selected == "Public":
        uid = "PUBLIC"
    elif not uid:
        return



    if client is None:
        print("MQTT client is not available. Cannot connect to a chat server.")
        return

    if not client.is_connected():
        try:
            client.connect(SERVER, 1883, 60)
        except Exception as error:
            print("Warning: failed to reconnect MQTT:", error)
            return

    TOPIC = f"VISCORD/{uid}"
    print ("Subscribing to topic:", TOPIC)

    client.subscribe(TOPIC)
    client.publish(TOPIC, f"System: {Name} has joined the server")
    

    login.withdraw()
    CHAT(Name, uid)


LoginButton = Button(
    login,
    text="Join Chat",
    command=Connect,
    bg=ACCENT,
    fg="white",
    font=("Arial", 12, "bold"),
    relief=FLAT
)
LoginButton.pack(pady=20)

login.mainloop()