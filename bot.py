import discord
from discord import app_commands
import json
import requests
import base64
import hashlib

# =========================
# CONFIG (NORMAL – NO ENV)
# =========================

import os

DISCORD_BOT_TOKEN = os.getenv("DISCORD")
GITHUB_TOKEN = os.getenv("GITHUB")


REPO = "SagarKumarGupta08/Discord-Auth"   # username/repo
FILE_PATH = "users.json"
BRANCH = "main"

# Admin Discord IDs
ADMIN_IDS = [
    777857263548497920,   # apna Discord ID
]

API_URL = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# =========================
# HELPERS
# =========================

def is_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.id in ADMIN_IDS

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    r = requests.get(API_URL, headers=HEADERS)
    if r.status_code == 200:
        content = r.json()["content"]
        decoded = base64.b64decode(content).decode()
        return json.loads(decoded)
    return {}

def save_users(data):
    r = requests.get(API_URL, headers=HEADERS)
    sha = r.json()["sha"]

    encoded = base64.b64encode(
        json.dumps(data, indent=4).encode()
    ).decode()

    payload = {
        "message": "Update users.json via Discord bot",
        "content": encoded,
        "branch": BRANCH,
        "sha": sha
    }

    requests.put(API_URL, headers=HEADERS, json=payload)

# =========================
# DISCORD SETUP
# =========================

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot online as {client.user}")

# =========================
# COMMANDS
# =========================


class AuthPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create User", style=discord.ButtonStyle.primary)
    async def create_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🆕 Use command:\n`/create username password expiry`",
            ephemeral=True
        )

    @discord.ui.button(label="Delete User", style=discord.ButtonStyle.danger)
    async def delete_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🗑️ Use command:\n`/delete username`",
            ephemeral=True
        )

    @discord.ui.button(label="Reset HWID", style=discord.ButtonStyle.secondary)
    async def reset_hwid(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🔄 Use command:\n`/reset_hwid username`",
            ephemeral=True
        )

    @discord.ui.button(label="Pause User", style=discord.ButtonStyle.secondary)
    async def pause_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "⏸️ Use command:\n`/pause username`",
            ephemeral=True
        )

    @discord.ui.button(label="Unpause User", style=discord.ButtonStyle.secondary)
    async def unpause_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "▶️ Use command:\n`/unpause username`",
            ephemeral=True
        )

    @discord.ui.button(label="Close Auth", style=discord.ButtonStyle.danger)
    async def close_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()




@tree.command(name="create", description="Create new user")
async def create(interaction: discord.Interaction, username: str, password: str, expiry: str):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Admin only", ephemeral=True)
        return

    users = load_users()

    if username in users:
        await interaction.response.send_message("❌ User already exists")
        return

    users[username] = {
        "password": hash_password(password),
        "expiry": expiry,
        "paused": False,
        "hwid": None
    }

    save_users(users)
    await interaction.response.send_message(f"✅ User `{username}` created")

@tree.command(name="delete", description="Delete user")
async def delete(interaction: discord.Interaction, username: str):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Admin only", ephemeral=True)
        return

    users = load_users()

    if username not in users:
        await interaction.response.send_message("❌ User not found")
        return

    del users[username]
    save_users(users)
    await interaction.response.send_message(f"🗑️ `{username}` deleted")

@tree.command(name="pause", description="Pause user")
async def pause(interaction: discord.Interaction, username: str):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Admin only", ephemeral=True)
        return

    users = load_users()
    users[username]["paused"] = True
    save_users(users)
    await interaction.response.send_message(f"⏸️ `{username}` paused")

@tree.command(name="unpause", description="Unpause user")
async def unpause(interaction: discord.Interaction, username: str):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Admin only", ephemeral=True)
        return

    users = load_users()
    users[username]["paused"] = False
    save_users(users)
    await interaction.response.send_message(f"▶️ `{username}` unpaused")

@tree.command(name="reset_hwid", description="Reset HWID")
async def reset_hwid(interaction: discord.Interaction, username: str):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Admin only", ephemeral=True)
        return

    users = load_users()

    if username not in users:
        await interaction.response.send_message("❌ User not found")
        return

    users[username]["hwid"] = None
    save_users(users)
    await interaction.response.send_message(f"🔄 HWID reset for `{username}`")

@tree.command(name="list", description="List all users")
async def list_users(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Admin only", ephemeral=True)
        return

    users = load_users()

    if not users:
        await interaction.response.send_message("📭 No users")
        return

    msg = "**👥 Users List**\n"
    for u, d in users.items():
        status = "⏸️ Paused" if d["paused"] else "✅ Active"
        msg += f"`{u}` | {status} | Expiry: {d['expiry']}\n"

    await interaction.response.send_message(msg)

@tree.command(name="count", description="Total users")
async def count(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ Admin only", ephemeral=True)
        return

    users = load_users()
    await interaction.response.send_message(f"📊 Total users: **{len(users)}**")


@tree.command(name="csharp_login_txt", description="Send C# login code txt file")
async def csharp_login_txt(interaction: discord.Interaction):

    code_text = """private void btnLogin_Click(object sender, EventArgs e)
{
    lblStatus.Text = "Checking...";

    string username = txtUser.Text.Trim();
    string password = txtPass.Text.Trim();

    if (username == "" || password == "")
    {
        lblStatus.Text = "Enter username & password";
        return;
    }

    try
    {
        string url = "https://raw.githubusercontent.com/SagarKumarGupta08/auth-db999/main/users.json";

        using (WebClient wc = new WebClient())
        {
            string json = wc.DownloadString(url);
            JObject users = JObject.Parse(json);

            if (users[username] == null)
            {
                lblStatus.Text = "Invalid username";
                return;
            }

            string dbPass = users[username]["password"].ToString();
            bool paused = (bool)users[username]["paused"];
            DateTime expiry = DateTime.Parse(users[username]["expiry"].ToString());

            if (paused)
            {
                lblStatus.Text = "Account paused";
                return;
            }

            if (DateTime.Now > expiry)
            {
                lblStatus.Text = "Account expired";
                return;
            }

            if (password != dbPass)
            {
                lblStatus.Text = "Wrong password";
                return;
            }

            lblStatus.Text = "Login success";

            Form2 f = new Form2();
            f.Show();
            this.Hide();
        }
    }
    catch (Exception ex)
    {
        lblStatus.Text = "Server error";
    }
}
"""

    # txt file create
    with open("login_code.txt", "w", encoding="utf-8") as f:
        f.write(code_text)

    # send file
    await interaction.response.send_message(
        content="📄 C# Login code file:",
        file=discord.File("login_code.txt")
    )


@tree.command(name="all", description="Open Auth Control Panel")
async def all(interaction: discord.Interaction):
    await interaction.response.send_message(
        content="🔐 **Auth Control Panel**",
        view=AuthPanel()
    )


# =========================
# RUN BOT
# =========================

client.run(DISCORD_BOT_TOKEN)