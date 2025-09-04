import asyncio
import csv
import subprocess
from pathlib import Path
from typing import Union

from dotenv import load_dotenv
from pydantic import BaseModel
from browser_use import Agent, BrowserProfile, BrowserSession, Controller
from langchain_openai import ChatOpenAI
from temp_email_sub_scan import create_account, wait_for_email_with_link

# Use browser-use version 0.2.5 (separate from etherscan)
load_dotenv()

# ---------- Output model ----------


class APIKey(BaseModel):
    api_key: str


# ---------- LLM & controller (reuse across runs) ----------
controller = Controller(output_model=APIKey)
llm = ChatOpenAI(model="gpt-4o")

# ---------- Timeouts ----------
TIMEOUT_SECONDS = 1000  # keep as you set; adjust if needed

# ---------- Cleanup helpers ----------
PROFILE_DIR = Path.home() / ".config" / "browseruse" / "profiles" / "default"


def _pkill(pattern: str) -> None:
    """Best-effort kill by pattern (Linux/GitHub Actions friendly)."""
    try:
        subprocess.run(["pkill", "-f", pattern], check=False)
    except FileNotFoundError:
        pass
    except Exception:
        pass


def cleanup_chrome_profile() -> None:
    """Kill lingering Chromium/Chrome and remove profile lock files."""
    for pat in (
        "chrome-linux/chrome",
        "Chromium",
        "chrome --type",
        "playwright",
    ):
        _pkill(pat)
    try:
        if PROFILE_DIR.exists():
            for p in PROFILE_DIR.glob("Singleton*"):
                try:
                    p.unlink()
                except Exception:
                    pass
    except Exception:
        pass

# ---------- Core run ----------


async def get_api() -> Union[str, None]:
    temp_email, token = create_account()
    print(f"📧 Temporary email: {temp_email}")
    password = "StrongPass123!"

    # Build a fresh browser session per run (so we can close it cleanly)
    browser_profile = BrowserProfile(
        headless=False,                 # headful (Xvfb/noVNC) is CF-friendly
        chromium_sandbox=False,         # keep as per your env
        default_timeout=120000,         # 120s per action
        default_navigation_timeout=120000,
        window_size={"width": 1650, "height": 800},
        viewport={"width": 1650, "height": 800},
        no_viewport=False,
        # Using the default persistent profile path; cleanup will unlock it
    )
    browser_session = BrowserSession(browser_profile=browser_profile)

    try:
        # Step 1: Sign up on Subscan
        signup_task = (
            f"You are creating a new account on Subscan. Follow these steps:\n"
            f"1. Open https://pro.subscan.io/signup/email\n"
            f"2. Complete the Sign-Up:\n"
            f"   Under 'Email' enter: {temp_email}\n"
            f"   Under 'Password' enter: {password}\n"
            f"   Under 'Confirm Password' enter: {password}\n"
            f"3. There is a checkbox below the 'Confirm Password' field and to the left of the text 'I have agree...'. "
            f"Click that checkbox to agree to terms (it is the 6th indexed item in that page). DO NOT click on the label or link.\n"
            f"4. Then click the 'Sign Up' button to submit the form.\n"
            f"4. Click on the 'Products' section in the top menu.\n"
            f"5. Under 'Products', click on 'API Service'.\n"
            f"6. If you see a verification prompt or message, look for a 'Resend Email' button and click it and finish "
            f"(DO NOT wait 2 minutes even if the webpage suggests it. After you've clicked the 'Resend Email' - finish the task right away).\n"
        )
        await Agent(task=signup_task, llm=llm, controller=controller, browser_session=browser_session).run()
        print("✅ Signup submitted.")

        # Step 2: Wait for verification email (up to 30 seconds)
        print("⏳ Waiting for verification email...")
        email_data = wait_for_email_with_link(token, timeout=30, interval=10)
        if not email_data or not email_data.get("link"):
            print("❌ No verification email received.")
            return None

        verification_link = email_data["link"]
        print(f"📨 Verification link: {verification_link}")

        # Small delay before following the link
        print("🕒 Waiting 10 seconds before visiting verification link...")
        await asyncio.sleep(10)

        # Step 3: Verify and create API key
        verification_andapi_key_task = (
            f"Complete the email verification:\n"
            f"1. Open the following verification link in your current tab:\n"
            f"{verification_link}\n"
            f"2. Click on the 'Products' section in the top menu.\n"
            f"3. Under 'Products', click on 'API Service'.\n"
            f"4. Click on 'API Key'.\n"
            f"5. Enter 'Sinai' as the app name.\n"
            f"6. Click 'Create New API Key'.\n"
            f"7. Click the small button to the left of the copy API token one to reveal the API token (so it will be without *************). "
            f"The icon of this button is a closed eye icon (that means that the API Key Token is hidden).\n"
            f"8. Only after the last stage, click the small copy icon to copy the API key.\n"
            f"9. If the API Key you copied has asterisks in it - return to step 7. If not - continue to the next step.\n"
            f"10. Return only the API key as JSON:\n"
            f'{{"api_key": "<your_key_here>"}}'
        )

        agent = Agent(task=verification_andapi_key_task, llm=llm,
                      controller=controller, browser_session=browser_session)
        result = await agent.run()
        print("✅ Email verification completed, API key copied and ready to be returned.")

        data = result.final_result()
        try:
            parsed = APIKey.model_validate_json(data)
            return parsed.api_key
        except Exception as e:
            print(f"⚠️ Failed to parse API key: {e}")
            print(f"Raw result: {data}")
            return None

    finally:
        # Clean shutdown of the browser/session + profile unlock
        try:
            await browser_session.close()
        except Exception as e:
            print(f"⚠️ browser_session.close() failed: {e}")
        cleanup_chrome_profile()

# ---------- CSV writer ----------


def write_csv(api_key: str, filename="sub_scan_api_keys.csv") -> None:
    with open(filename, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([api_key])
    print(f"✅ API key saved to '{filename}'.")

# ---------- Loop ----------


async def run_multiple_keys(n: int = 1):
    for i in range(n):
        print(f"\n🔁 Starting run {i + 1} of {n}")
        try:
            key = await asyncio.wait_for(get_api(), timeout=TIMEOUT_SECONDS)
            if key:
                write_csv(key)
                print(f"✅ Successfully generated API key: {key[:10]}...")
            else:
                print("⚠️ No key returned.")
        except asyncio.TimeoutError:
            mins = TIMEOUT_SECONDS // 60
            print(
                f"⏰ Timeout: API generation run {i + 1} exceeded {mins} minutes.")
        except Exception as e:
            print(f"❌ Error in run {i + 1}: {e}")
        finally:
            # Safety cleanup after each iteration + a short breather
            cleanup_chrome_profile()
            await asyncio.sleep(1.0)

if __name__ == "__main__":
    try:
        asyncio.run(run_multiple_keys(10))
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user.")
