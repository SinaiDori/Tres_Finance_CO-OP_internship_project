# from temp_email_etherscan import create_account, wait_for_email_with_link
# from langchain_openai import ChatOpenAI
# from browser_use import Agent, Controller
# import asyncio
# import csv
# import time
# import requests
# from typing import Union
# from dotenv import load_dotenv
# from pydantic import BaseModel

# # Use browser-use version 0.1.45 only!

# load_dotenv()

# # Output format


# class APIKey(BaseModel):
#     api_key: str


# # To prevent endless-loops
# TIMEOUT_SECONDS = 1000

# # Generating the keys using functions from temp_email.py


# async def get_api() -> Union[str, None]:
#     temp_email, token = create_account()
#     print(f"📧 Temporary email: {temp_email}")
#     username = temp_email.split("@")[0]
#     password = "StrongPass123!"
#     controller = Controller(output_model=APIKey)
#     llm = ChatOpenAI(model="gpt-4o")

#     # 1. Sign-up
#     signup_task = (
#         f"You are creating a new account on Etherscan. Follow these steps:\n"
#         f"1. Open https://etherscan.io/register\n"
#         f"2. Complete the Sign-Up:\n"
#         f"- Under 'Username' enter: {username}\n"
#         f"- Under 'Email Adress' enter: {temp_email}\n"
#         f"- Under 'Confirm Email Adress' enter: {temp_email}\n"
#         f"- Under 'Password' enter: {password}\n"
#         f"- Under 'Confirm Password' enter: {password}\n"
#         "3. Click the 'Got it' button to accept the cookies.\n"
#         "4. Check the 'I agree to the Terms and Conditions' box."
#         "5. Scroll down and click 'Create an Account'.\n"
#         "6. Finish the task.\n"
#     )
#     await Agent(task=signup_task, llm=llm, controller=controller).run()
#     print("✅ Signup submitted.")

#     # 2. Email verification
#     print("⏳ Waiting for confirmation email...")
#     email_data = wait_for_email_with_link(token, timeout=30, interval=10)
#     if not email_data or not email_data.get("link"):
#         print("❌ No verification email received.")
#         return None

#     verification_link = email_data["link"]
#     print("🕒 Verifying email via HTTP request (no browser)…")
#     if not confirm_etherscan_email(verification_link):
#         print("❌ Email verification request did not confirm successfully.")
#         return None
#     print("✅ Email verified.")

#     # 3. Login + get API key
#     verification_andapi_key_task = (
#         f"Open https://etherscan.io/login\n"
#         f"1. Sign in using the following credentials:\n"
#         f"- Username: {username}\n"
#         f"- Password: {password}\n"
#         f"2. Click on 'LOGIN'.\n"
#         f"4. Scroll a bit down to find the 'API Dashboard' button on the left side menu unser 'OTHERS' and click on it.\n"
#         f"6. Find the '+ Add' button and click on it to create a new API key.\n"
#         f"7. Enter 'Sinai' as the app name.\n"
#         f"8. Click 'Create New API Key'.\n"
#         f"9. Scroll down and click the small Copy API Key Token icon to copy the API key.\n"
#         f"10. Return only the API key as JSON:\n"
#         f"{{\"api_key\": \"<your_key_here>\"}}"
#         f"11. Finish the task.\n"
#         f"GENERAL NOTE: If at any point you don't see what you are supposed to see - try to scroll a bit down or up.\n"
#     )

#     fresh_controller = Controller(output_model=APIKey)
#     fresh_llm = ChatOpenAI(model="gpt-4o")
#     agent = Agent(task=verification_andapi_key_task,
#                   llm=fresh_llm, controller=fresh_controller)
#     result = await agent.run()
#     print("✅ Email verification completed, API key copied and ready to be returned.")

#     data = result.final_result()
#     try:
#         parsed = APIKey.model_validate_json(data)
#         return parsed.api_key
#     except Exception as e:
#         print(f"⚠️ Failed to parse API key: {e}")
#         return None

# # confirming the email using the verification link


# def confirm_etherscan_email(verification_link: str, timeout: int = 30) -> bool:
#     """
#     Visits the verification link with a real browser UA and follows redirects.
#     Returns True if the request likely verified the email.
#     """
#     headers = {
#         "User-Agent": (
#             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
#             "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
#         ),
#         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#         "Accept-Language": "en-US,en;q=0.9",
#         "Referer": "https://etherscan.io/",
#         "Connection": "close",
#     }
#     try:
#         # Small delay can help if the provider hasn't propagated the token yet
#         time.sleep(2)
#         r = requests.get(verification_link, headers=headers,
#                          timeout=timeout, allow_redirects=True)
#         # Heuristics: Etherscan typically redirects to /login after success,
#         # or shows a "verified/confirmed" message.
#         if r.status_code in (200, 301, 302):
#             text = (r.text or "").lower()
#             final_path = r.url.lower()
#             if ("verified" in text or "confirmation" in text or "confirmed" in text):
#                 return True
#             if "/login" in final_path:
#                 return True
#         return False
#     except requests.RequestException as e:
#         print(f"HTTP error while confirming email: {e}")
#         return False


# # Writing the api key to csv


# def write_csv(api_key: str, filename="etherscan_api_keys.csv") -> None:
#     with open(filename, "a", newline="") as csvfile:
#         writer = csv.writer(csvfile)
#         writer.writerow([api_key])
#     print(f"✅ API key saved to '{filename}'.")

# # Running the script in a loop


# async def run_multiple_keys(n: int = 1):
#     for i in range(n):
#         print(f"\n🔁 Starting run {i + 1} of {n}")
#         try:
#             key = await asyncio.wait_for(get_api(), timeout=TIMEOUT_SECONDS)
#             if key:
#                 write_csv(key)
#                 print(f"✅ Successfully generated API key: {key[:10]}...")
#             else:
#                 print("⚠️ No key returned.")
#         except asyncio.TimeoutError:
#             print(
#                 f"⏰ Timeout: API generation run {i + 1} took longer than {TIMEOUT_SECONDS // 60} minutes.")

# if __name__ == "__main__":
#     try:
#         asyncio.run(run_multiple_keys(1))
#     except KeyboardInterrupt:
#         print("🛑 Interrupted by user.")

from temp_email_etherscan import create_account, wait_for_email_with_link
from langchain_openai import ChatOpenAI
from browser_use import Agent, Controller
from browser_use.browser.context import BrowserContextConfig
import asyncio
import csv
import time
import requests
import random
import os
from typing import Union
from dotenv import load_dotenv
from pydantic import BaseModel

# Use browser-use version 0.1.45 only!
load_dotenv()

# Output format


class APIKey(BaseModel):
    api_key: str


# To prevent endless-loops
TIMEOUT_SECONDS = 1000


def get_browser_config():
    """Create a realistic browser configuration to avoid detection"""
    # List of realistic user agents
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
    ]

    # List of realistic timezones
    timezones = [
        "America/New_York",
        "Europe/London",
        "Europe/Paris",
        "Asia/Tokyo",
        "Australia/Sydney"
    ]

    return BrowserContextConfig(
        user_agent=random.choice(user_agents),
        viewport={"width": random.randint(
            1200, 1920), "height": random.randint(800, 1080)},
        locale="en-US,en;q=0.9",
        timezone_id=random.choice(timezones),
        geolocation={
            "longitude": random.uniform(-180, 180),
            "latitude": random.uniform(-90, 90),
            "accuracy": random.uniform(10, 100)
        },
        permissions=["geolocation", "notifications", "microphone", "camera"],
        extra_http_headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        },
        # Enable more realistic behavior
        enable_biometric_emulation=True,
        # Add some browser features to appear more legitimate
        features={
            "canvas": True,
            "webgl": True,
            "audio": True,
            "video": True
        }
    )

# Generating the keys using functions from temp_email.py


async def get_api() -> Union[str, None]:
    temp_email, token = create_account()
    print(f"📧 Temporary email: {temp_email}")
    username = temp_email.split("@")[0]
    password = "StrongPass123!"

    browser_config = get_browser_config()
    controller = Controller(output_model=APIKey, browser_config=browser_config)
    llm = ChatOpenAI(model="gpt-4o")

    # 1. Sign-up
    signup_task = (
        f"You are creating a new account on Etherscan. Follow these steps:\n"
        f"1. Open https://etherscan.io/register\n"
        f"2. Complete the Sign-Up:\n"
        f"- Under 'Username' enter: {username}\n"
        f"- Under 'Email Adress' enter: {temp_email}\n"
        f"- Under 'Confirm Email Adress' enter: {temp_email}\n"
        f"- Under 'Password' enter: {password}\n"
        f"- Under 'Confirm Password' enter: {password}\n"
        "3. Click the 'Got it' button to accept the cookies.\n"
        "4. Check the 'I agree to the Terms and Conditions' box."
        "5. Scroll down and click 'Create an Account'.\n"
        "6. If you encounter a Cloudflare security check, wait for it to complete or solve it if needed.\n"
        "7. Finish the task.\n"
    )

    # Add random delays between actions
    agent = Agent(
        task=signup_task,
        llm=llm,
        controller=controller,
        # Longer random delay between actions
        action_delay=random.uniform(2, 5)
    )
    await agent.run()
    print("✅ Signup submitted.")

    # 2. Email verification
    print("⏳ Waiting for confirmation email...")
    email_data = wait_for_email_with_link(token, timeout=30, interval=10)
    if not email_data or not email_data.get("link"):
        print("❌ No verification email received.")
        return None

    verification_link = email_data["link"]
    print("🕒 Verifying email via HTTP request (no browser)…")

    if not confirm_etherscan_email(verification_link):
        print("❌ Email verification request did not confirm successfully.")
        return None
    print("✅ Email verified.")

    # 3. Login + get API key
    verification_andapi_key_task = (
        f"Open https://etherscan.io/login\n"
        f"1. Sign in using the following credentials:\n"
        f"- Username: {username}\n"
        f"- Password: {password}\n"
        f"2. Click on 'LOGIN'.\n"
        f"3. If you encounter a Cloudflare security check, wait for it to complete or solve it if needed.\n"
        f"4. Scroll a bit down to find the 'API Dashboard' button on the left side menu under 'OTHERS' and click on it.\n"
        f"5. Find the '+ Add' button and click on it to create a new API key.\n"
        f"6. Enter 'Sinai' as the app name.\n"
        f"7. Click 'Create New API Key'.\n"
        f"8. Scroll down and click the small Copy API Key Token icon to copy the API key.\n"
        f"9. Return only the API key as JSON:\n"
        f"{{\"api_key\": \"<your_key_here>\"}}"
        f"10. Finish the task.\n"
        f"GENERAL NOTE: If at any point you don't see what you are supposed to see - try to scroll a bit down or up.\n"
        f"IMPORTANT: Take your time between actions and behave like a human user.\n"
    )

    fresh_controller = Controller(
        output_model=APIKey, browser_config=get_browser_config())
    fresh_llm = ChatOpenAI(model="gpt-4o")
    agent = Agent(
        task=verification_andapi_key_task,
        llm=fresh_llm,
        controller=fresh_controller,
        # Longer random delay between actions
        action_delay=random.uniform(2, 5)
    )
    result = await agent.run()
    print("✅ Email verification completed, API key copied and ready to be returned.")

    data = result.final_result()
    try:
        parsed = APIKey.model_validate_json(data)
        return parsed.api_key
    except Exception as e:
        print(f"⚠️ Failed to parse API key: {e}")
        return None

# confirming the email using the verification link


def confirm_etherscan_email(verification_link: str, timeout: int = 30) -> bool:
    """
    Visits the verification link with a real browser UA and follows redirects.
    Returns True if the request likely verified the email.
    """
    # Rotate user agents for the verification request
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]

    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://etherscan.io/",
        "Connection": "close",
    }

    try:
        # Add a small random delay
        time.sleep(random.uniform(1, 3))
        r = requests.get(verification_link, headers=headers,
                         timeout=timeout, allow_redirects=True)
        # Heuristics: Etherscan typically redirects to /login after success,
        # or shows a "verified/confirmed" message.
        if r.status_code in (200, 301, 302):
            text = (r.text or "").lower()
            final_path = r.url.lower()
            if ("verified" in text or "confirmation" in text or "confirmed" in text):
                return True
            if "/login" in final_path:
                return True
        return False
    except requests.RequestException as e:
        print(f"HTTP error while confirming email: {e}")
        return False

# Writing the api key to csv


def write_csv(api_key: str, filename="etherscan_api_keys.csv") -> None:
    with open(filename, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([api_key])
    print(f"✅ API key saved to '{filename}'.")

# Running the script in a loop


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
            print(
                f"⏰ Timeout: API generation run {i + 1} took longer than {TIMEOUT_SECONDS // 60} minutes.")

if __name__ == "__main__":
    try:
        asyncio.run(run_multiple_keys(1))
    except KeyboardInterrupt:
        print("🛑 Interrupted by user.")
