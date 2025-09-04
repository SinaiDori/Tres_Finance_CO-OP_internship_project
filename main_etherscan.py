from temp_email_etherscan import create_account, wait_for_email_with_link
from langchain_openai import ChatOpenAI
from browser_use import Agent, Controller
import asyncio
import csv
import time
import requests
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

# Generating the keys using functions from temp_email.py


async def get_api() -> Union[str, None]:
    temp_email, token = create_account()
    print(f"📧 Temporary email: {temp_email}")
    username = temp_email.split("@")[0]
    password = "StrongPass123!"
    controller = Controller(output_model=APIKey)
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
        "6. Finish the task.\n"
    )
    await Agent(task=signup_task, llm=llm, controller=controller).run()
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
        f"4. Scroll a bit down to find the 'API Dashboard' button on the left side menu unser 'OTHERS' and click on it.\n"
        f"6. Find the '+ Add' button and click on it to create a new API key.\n"
        f"7. Enter 'Sinai' as the app name.\n"
        f"8. Click 'Create New API Key'.\n"
        f"9. Scroll down and click the small Copy API Key Token icon to copy the API key.\n"
        f"10. Return only the API key as JSON:\n"
        f"{{\"api_key\": \"<your_key_here>\"}}"
        f"11. Finish the task.\n"
        f"GENERAL NOTE: If at any point you don't see what you are supposed to see - try to scroll a bit down or up.\n"
    )

    fresh_controller = Controller(output_model=APIKey)
    fresh_llm = ChatOpenAI(model="gpt-4o")
    agent = Agent(task=verification_andapi_key_task,
                  llm=fresh_llm, controller=fresh_controller)
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
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://etherscan.io/",
        "Connection": "close",
    }
    try:
        # Small delay can help if the provider hasn't propagated the token yet
        time.sleep(2)
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
        asyncio.run(run_multiple_keys(10))
    except KeyboardInterrupt:
        print("🛑 Interrupted by user.")
# from temp_email_etherscan import create_account, wait_for_email_with_link
# from browser_use.llm import ChatOpenAI
# from browser_use import Agent, BrowserSession
# from browser_use.browser import BrowserProfile
# import asyncio
# import csv
# import time
# import requests
# from typing import Union
# from dotenv import load_dotenv
# from pydantic import BaseModel
# import os

# load_dotenv()


# class APIKey(BaseModel):
#     api_key: str


# TIMEOUT_SECONDS = 1000


# async def get_api_with_browserless() -> Union[str, None]:
#     """Enhanced version using browserless cloud with Cloudflare bypass"""
#     temp_email, token = create_account()
#     print(f"📧 Temporary email: {temp_email}")
#     username = temp_email.split("@")[0]
#     password = "StrongPass123!"

#     # Try BrowserQL REST API first (more reliable for Cloudflare bypass)
#     test_result = await get_api_browserql_rest()
#     if test_result:
#         return test_result

#     # Get browserless token from environment
#     browserless_token = os.getenv('BROWSERLESS_API_TOKEN')
#     if not browserless_token:
#         raise ValueError(
#             "BROWSERLESS_API_TOKEN environment variable is required")

#     # Configure browserless session with stealth features
#     browser_session = BrowserSession(
#         cdp_url=f"wss://production-ams.browserless.io?token={browserless_token}&--disable-web-security&--disable-features=VizDisplayCompositor",
#         browser_profile=BrowserProfile(
#             user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
#             viewport_size={"width": 1920, "height": 1080},
#             headless=True,
#             extra_headers={
#                 "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
#                 "Accept-Language": "en-US,en;q=0.9",
#                 "Accept-Encoding": "gzip, deflate, br, zstd",
#                 "Sec-Ch-Ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
#                 "Sec-Ch-Ua-Platform": '"macOS"',
#                 "DNT": "1"
#             }
#         )
#     )

#     llm = ChatOpenAI(model="gpt-4o")

#     # 1. Enhanced signup with Cloudflare handling
#     signup_task = (
#         f"You are creating a new account on Etherscan using browserless which can handle Cloudflare challenges. Follow these steps:\n"
#         f"1. Open https://etherscan.io/register\n"
#         f"2. Check the box of 'verify you are a human'.\n"
#         f"3. Complete the Sign-Up:\n"
#         f"- Under 'Username' enter: {username}\n"
#         f"- Under 'Email Address' enter: {temp_email}\n"
#         f"- Under 'Confirm Email Address' enter: {temp_email}\n"
#         f"- Under 'Password' enter: {password}\n"
#         f"- Under 'Confirm Password' enter: {password}\n"
#         f"4. If you see a 'Got it' button for cookies, click it.\n"
#         f"5. Check the 'I agree to the Terms and Conditions' box.\n"
#         f"6. Scroll down and click 'Create an Account'.\n"
#         f"7. Wait for any additional Cloudflare verification if needed.\n"
#         f"8. Finish the task.\n"
#     )

#     try:
#         # Run signup task with browserless handling Cloudflare automatically
#         agent = Agent(task=signup_task, llm=llm,
#                       browser_session=browser_session)
#         await agent.run()
#         print("✅ Signup submitted with Cloudflare bypass.")

#     except Exception as e:
#         print(f"❌ Signup failed: {e}")
#         return None

#     # 2. Email verification (same as before)
#     print("⏳ Waiting for confirmation email...")
#     email_data = wait_for_email_with_link(token, timeout=60, interval=10)
#     if not email_data or not email_data.get("link"):
#         print("❌ No verification email received.")
#         return None

#     verification_link = email_data["link"]
#     print("🕒 Verifying email via HTTP request...")
#     if not confirm_etherscan_email(verification_link):
#         print("❌ Email verification failed.")
#         return None
#     print("✅ Email verified.")

#     # 3. Enhanced login and API key generation
#     # Create new browser session for login
#     browser_session = BrowserSession(
#         cdp_url=f"wss://production-sfo.browserless.io?token={browserless_token}&proxy=residential",
#         browser_profile=BrowserProfile(
#             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
#             viewport_size={"width": 1920, "height": 1080},
#             headless=True,
#         )
#     )

#     api_key_task = (
#         f"Login to Etherscan and generate API key using browserless (handles Cloudflare automatically):\n"
#         f"1. Open https://etherscan.io/login\n"
#         f"2. Wait for Cloudflare challenges to complete if any appear\n"
#         f"3. Sign in using:\n"
#         f"   - Username: {username}\n"
#         f"   - Password: {password}\n"
#         f"4. Click 'LOGIN' and wait for any additional verification\n"
#         f"5. Navigate to API Dashboard:\n"
#         f"   - Look for 'API Dashboard' in the left menu under 'OTHERS'\n"
#         f"   - Click on 'API Dashboard'\n"
#         f"6. Create new API key:\n"
#         f"   - Find and click the '+ Add' button\n"
#         f"   - Enter 'Sinai' as the app name\n"
#         f"   - Click 'Create New API Key'\n"
#         f"7. Copy the API key:\n"
#         f"   - Scroll to find your new API key\n"
#         f"   - Click the copy icon next to the API key\n"
#         f"8. Return the API key in this exact JSON format:\n"
#         f"   {{\"api_key\": \"your_actual_key_here\"}}\n"
#         f"IMPORTANT: If you encounter any Cloudflare blocks, just wait - browserless will handle them automatically.\n"
#     )

#     try:
#         agent = Agent(task=api_key_task, llm=llm,
#                       browser_session=browser_session)
#         result = await agent.run()
#         print("✅ Login and API key generation completed.")

#         # Parse the API key from result
#         final_result = result.final_result() if hasattr(
#             result, 'final_result') else str(result)
#         try:
#             parsed = APIKey.model_validate_json(final_result)
#             return parsed.api_key
#         except Exception as e:
#             print(f"⚠️ Failed to parse API key: {e}")
#             print(f"Raw result: {final_result}")
#             return None

#     except Exception as e:
#         print(f"❌ Login failed: {e}")
#         return None


# def confirm_etherscan_email(verification_link: str, timeout: int = 30) -> bool:
#     """Enhanced email confirmation with better headers"""
#     headers = {
#         "User-Agent": (
#             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
#             "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
#         ),
#         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#         "Accept-Language": "en-US,en;q=0.9",
#         "Accept-Encoding": "gzip, deflate, br",
#         "DNT": "1",
#         "Connection": "keep-alive",
#         "Upgrade-Insecure-Requests": "1",
#         "Sec-Fetch-Dest": "document",
#         "Sec-Fetch-Mode": "navigate",
#         "Sec-Fetch-Site": "same-origin",
#         "Cache-Control": "max-age=0",
#     }

#     try:
#         time.sleep(3)  # Allow email system to propagate
#         response = requests.get(
#             verification_link,
#             headers=headers,
#             timeout=timeout,
#             allow_redirects=True
#         )

#         if response.status_code in (200, 301, 302):
#             text = response.text.lower()
#             final_url = response.url.lower()

#             success_indicators = [
#                 "verified" in text,
#                 "confirmation" in text,
#                 "confirmed" in text,
#                 "/login" in final_url,
#                 "success" in text
#             ]

#             if any(success_indicators):
#                 return True

#         print(
#             f"🔍 Email verification response: {response.status_code} -> {response.url}")
#         return False

#     except requests.RequestException as e:
#         print(f"❌ HTTP error during email confirmation: {e}")
#         return False


# def write_csv(api_key: str, filename="etherscan_api_keys.csv") -> None:
#     """Save API key to CSV file"""
#     with open(filename, "a", newline="") as csvfile:
#         writer = csv.writer(csvfile)
#         writer.writerow([api_key])
#     print(f"✅ API key saved to '{filename}'.")


# async def run_multiple_keys_browserless(n: int = 1):
#     """Enhanced version using browserless for better Cloudflare bypass"""
#     print("🚀 Starting enhanced Etherscan API generation with browserless...")
#     print("🔐 Browserless will automatically handle Cloudflare challenges")

#     for i in range(n):
#         print(f"\n🔁 Starting run {i + 1} of {n}")
#         try:
#             key = await asyncio.wait_for(get_api_with_browserless(), timeout=TIMEOUT_SECONDS)
#             if key:
#                 write_csv(key)
#                 print(f"✅ Successfully generated API key: {key[:10]}...")
#             else:
#                 print("⚠️ No key returned.")
#         except asyncio.TimeoutError:
#             print(
#                 f"⏰ Timeout: API generation run {i + 1} took longer than {TIMEOUT_SECONDS // 60} minutes.")
#         except Exception as e:
#             print(f"❌ Error in run {i + 1}: {e}")


# # Alternative: Using BrowserQL REST API approach (even more stealth)
# async def get_api_browserql_rest() -> Union[str, None]:
#     """Alternative using BrowserQL REST API for maximum stealth"""
#     browserless_token = os.getenv('BROWSERLESS_API_TOKEN')

#     # BrowserQL unblock endpoint for Cloudflare bypassing
#     browserql_url = "https://production-sfo.browserless.io/unblock"
#     headers = {
#         "Authorization": f"Bearer {browserless_token}",
#         "Content-Type": "application/json"
#     }

#     # Test if we can access Etherscan through BrowserQL
#     etherscan_test_payload = {
#         "url": "https://etherscan.io/register",
#         "content": True,
#         "ttl": 30000
#     }

#     try:
#         print("🔍 Testing BrowserQL access to Etherscan...")
#         response = requests.post(
#             browserql_url, headers=headers, json=etherscan_test_payload)
#         if response.status_code == 200:
#             print("✅ BrowserQL successfully bypassed Cloudflare for Etherscan")
#             # Fallback to browser-use agent for form filling
#             return await get_api_with_browserless()
#         else:
#             print(f"❌ BrowserQL failed: {response.status_code}")
#             return None
#     except Exception as e:
#         print(f"❌ BrowserQL REST API error: {e}")
#         return None


# if __name__ == "__main__":
#     # Make sure you have BROWSERLESS_API_TOKEN in your .env file
#     try:
#         print("🌟 Enhanced Etherscan API Generator with Browserless Cloudflare Bypass")
#         print("📝 Make sure you have BROWSERLESS_API_TOKEN in your .env file")
#         asyncio.run(run_multiple_keys_browserless(1))
#     except KeyboardInterrupt:
#         print("🛑 Interrupted by user.")
#     except Exception as e:
#         print(f"❌ Fatal error: {e}")
