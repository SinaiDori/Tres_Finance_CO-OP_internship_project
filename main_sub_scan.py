import asyncio
import csv
from typing import Union
from dotenv import load_dotenv
from pydantic import BaseModel
# from browser_use import Agent, Controller
from browser_use import Agent, BrowserProfile, BrowserSession, Controller
from langchain_openai import ChatOpenAI
from temp_email_sub_scan import create_account, wait_for_email_with_link

# Use browser-use version 0.2.5, and not the same as etherscan

load_dotenv()

# Output format


class APIKey(BaseModel):
    api_key: str


controller = Controller(output_model=APIKey)
llm = ChatOpenAI(model="gpt-4o")
browser_profile = BrowserProfile(
    headless=False,  # Must be False to see the browser window
    chromium_sandbox=False,  # Disable sandbox for Browserless
    default_timeout=120000,  # 120s per action
    default_navigation_timeout=120000,  # 120s per navigation
    window_size={"width": 1650, "height": 800},  # Large window size
    viewport={"width": 1650, "height": 800},
    no_viewport=False,  # Explicitly enable viewport
)
browser_session = BrowserSession(browser_profile=browser_profile)


TIMEOUT_SECONDS = 1000

# Generating the keys using functions from temp_email.py


async def get_api() -> Union[str, None]:
    temp_email, token = create_account()
    print(f"📧 Temporary email: {temp_email}")
    password = "StrongPass123!"

    # Step 1: Sign up on Subscan
    signup_task = (
        f"You are creating a new account on Subscan. Follow these steps:\n"
        f"1. Open https://pro.subscan.io/signup/email\n"
        f"2. Complete the Sign-Up:\n"
        f" Under 'Email' enter: {temp_email}\n"
        f" Under 'Password' enter: {password}\n"
        f" Under 'Confirm Password' enter: {password}\n"
        f"3. There is a checkbox below the 'Confirm Password' field and to the left of the text 'I have agree...'. Click that checkbox to agree to terms (it is the 6th indexed item in that page). DO NOT click on the label or link.\n"
        f"4. Then click the 'Sign Up' button to submit the form.\n"
        f"4. Click on the 'Products' section in the top menu.\n"
        f"5. Under 'Products', click on 'API Service'.\n"
        f"6. If you see a verification prompt or message, look for a 'Resend Email' button and click it and finish (DO NOT wait 2 minutes even if the webpage suggests it. After you've clicked the 'Resend Email' - finish the task right away).\n"
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

    # Sleep for 10 seconds before proceeding
    print("🕒 Waiting 10 seconds before visiting verification link...")
    await asyncio.sleep(10)

    # Step 3: Complete email verification and create API key (now that verification is done)
    verification_andapi_key_task = (
        f"Complete the email verification:\n"
        f"1. Open the following verification link in your current tab:\n"
        f"{verification_link}\n"
        f"2. Click on the 'Products' section in the top menu.\n"
        f"3. Under 'Products', click on 'API Service'.\n"
        f"4. Click on 'API Key'.\n"
        f"5. Enter 'Sinai' as the app name.\n"
        f"6. Click 'Create New API Key'.\n"
        f"7. Click the small button to the left of the copy API token one to reveal the API token (so it will be without *************). The icon of this button is a closed eye icon (that means that the API Key Token is hidden).\n"
        f"8. Only after the last stage, click the small copy icon to copy the API key.\n"
        f"9. If the API Key you copied has astrics in it - return to step 7. If not - continue to the next step.\n"
        f"8. Return only the API key as JSON:\n"
        f"{{\"api_key\": \"<your_key_here>\"}}"
    )

    agent = Agent(task=verification_andapi_key_task,
                  llm=llm, controller=controller, browser_session=browser_session)
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

# Writing the api key to csv


def write_csv(api_key: str, filename="sub_scan_api_keys.csv") -> None:
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
        except Exception as e:
            print(f"❌ Error in run {i + 1}: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(run_multiple_keys(2))
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user.")

#######################################################################################################################
# import asyncio
# import csv
# import os
# from typing import Union
# from dotenv import load_dotenv
# from pydantic import BaseModel

# # --- LLM import ---
# # Prefer the browser_use built-in shim (v0.3+ / 0.6.x). If unavailable, fall back to your original.
# try:
#     # browser-use >= 0.3.x (recommended 0.6.x)
#     from browser_use.llm import ChatOpenAI
# except ImportError:
#     from langchain_openai import ChatOpenAI  # fallback for older setups

# # --- browser-use (CDP) ---
# from browser_use import Agent, BrowserSession, Controller
# from browser_use.browser import BrowserProfile

# from temp_email_sub_scan import create_account, wait_for_email_with_link

# # Use Browserless over CDP with browser-use (no local browser needed)
# load_dotenv()

# # Output format


# class APIKey(BaseModel):
#     api_key: str


# # Browserless configuration
# BROWSERLESS_API_KEY = os.getenv(
#     "BROWSERLESS_API_KEY")  # Add this to your .env file
# BROWSERLESS_ENDPOINT = f"wss://production-ams.browserless.io?token={BROWSERLESS_API_KEY}"
# # (If you later hit rate limits, you can change region manually, e.g. production-ams / production-lon.)

# controller = Controller(output_model=APIKey)
# llm = ChatOpenAI(model="gpt-4o")

# # # Create a remote browser session over CDP (resilient + debuggable)
# # browser_session = BrowserSession(
# #     cdp_url=BROWSERLESS_ENDPOINT,  # CDP endpoint for Browserless
# # )
# profile = BrowserProfile(
#     # Playwright timing settings
#     default_timeout=60000,               # 60s per action
#     default_navigation_timeout=90000,    # 90s per navigation

#     # Agent page-load patience (Browser Use settings)
#     wait_for_network_idle_page_load_time=5.0,
#     maximum_wait_page_load_time=20.0,
#     wait_between_actions=0.2,  # 200ms between actions
#     minimum_wait_page_load_time=1.0,  # 1s minimum wait time
# )

# browser_session = BrowserSession(
#     cdp_url=BROWSERLESS_ENDPOINT,
#     browser_profile=profile,             # <-- pass the profile here
# )

# # (left exactly as in your code; not changing per your request)
# TIMEOUT_SECONDS = 1000


# # Generating the keys using functions from temp_email_sub_scan.py
# async def get_api() -> Union[str, None]:
#     temp_email, token = create_account()
#     print(f"📧 Temporary email: {temp_email}")
#     print(f"🔗 Connecting to Browserless: {BROWSERLESS_ENDPOINT}")
#     password = "StrongPass123!"

#     # Step 1: Sign up on Subscan
#     signup_task = (
#         f"You are creating a new account on Subscan. Follow these steps:\n"
#         f"1. Open https://pro.subscan.io/signup/email\n"
#         f"2. Complete the Sign-Up:\n"
#         f" Under 'Email' enter: {temp_email}\n"
#         f" Under 'Password' enter: {password}\n"
#         f" Under 'Confirm Password' enter: {password}\n"
#         f"3. There is a checkbox below the 'Confirm Password' field and to the left of the text 'I have agree...'. Click that checkbox to agree to terms (it is the 6th indexed item in that page). DO NOT click on the label or link.\n"
#         f"4. Then click the 'Sign Up' button to submit the form.\n"
#         f"4. Click on the 'Products' section in the top menu.\n"
#         f"5. Under 'Products', click on 'API Service'.\n"
#         f"6. If you see a verification prompt or message, look for a 'Resend Email' button and click it and finish (DO NOT wait 2 minutes even if the webpage suggests it. After you've clicked the 'Resend Email' - finish the task right away).\n"
#     )

#     await Agent(
#         task=signup_task,
#         llm=llm,
#         controller=controller,
#         # <-- CDP session (not Browser/BrowserConfig)
#         browser_session=browser_session,
#     ).run()
#     print("✅ Signup submitted.")

#     # Step 2: Wait for verification email (up to 30 seconds)
#     print("⏳ Waiting for verification email...")
#     email_data = wait_for_email_with_link(token, timeout=30, interval=10)
#     if not email_data or not email_data.get("link"):
#         print("❌ No verification email received.")
#         return None

#     verification_link = email_data["link"]
#     print(f"📨 Verification link: {verification_link}")

#     # Sleep for 10 seconds before proceeding
#     print("🕐 Waiting 10 seconds before visiting verification link...")
#     await asyncio.sleep(10)

#     # Step 3: Complete email verification and create API key (now that verification is done)
#     verification_andapi_key_task = (
#         f"Complete the email verification:\n"
#         f"1. Open the following verification link in your current tab:\n"
#         f"{verification_link}\n"
#         f"2. Click on the 'Products' section in the top menu.\n"
#         f"3. Under 'Products', click on 'API Service'.\n"
#         f"4. Click on 'API Key'.\n"
#         f"5. Enter 'Sinai' as the app name.\n"
#         f"6. Click 'Create New API Key'.\n"
#         f"7. Click the small button to the left of the copy API token one to reveal the API token (so it will be without *************). The icon of this button is a closed eye icon (that means that the API Key Token is hidden).\n"
#         f"8. Only after the last stage, click the small copy icon to copy the API key.\n"
#         f"9. If the API Key you copied has astrics in it - return to step 7. If not - continue to the next step.\n"
#         f"8. Return only the API key as JSON:\n"
#         f"{{\"api_key\": \"<your_key_here>\"}}"
#     )

#     agent = Agent(
#         task=verification_andapi_key_task,
#         llm=llm,
#         controller=controller,
#         browser_session=browser_session,  # <-- CDP session
#     )
#     result = await agent.run()
#     print("✅ Email verification completed, API key copied and ready to be returned.")

#     data = result.final_result()
#     try:
#         parsed = APIKey.model_validate_json(data)
#         return parsed.api_key
#     except Exception as e:
#         print(f"⚠️ Failed to parse API key: {e}")
#         print(f"Raw result: {data}")
#         return None


# # Writing the api key to csv
# def write_csv(api_key: str, filename="sub_scan_api_keys.csv") -> None:
#     with open(filename, "a", newline="") as csvfile:
#         writer = csv.writer(csvfile)
#         writer.writerow([api_key])
#     print(f"✅ API key saved to '{filename}'.")


# # Running the script in a loop
# async def run_multiple_keys(n: int = 1):
#     for i in range(n):
#         print(f"\n🔄 Starting run {i + 1} of {n}")
#         try:
#             key = await asyncio.wait_for(get_api(), timeout=TIMEOUT_SECONDS)
#             if key:
#                 write_csv(key)
#                 print(f"✅ Successfully generated API key: {key[:10]}...")
#             else:
#                 print("⚠️ No key returned.")
#         except asyncio.TimeoutError:
#             print(
#                 f"⏰ Timeout: API generation run {i + 1} took longer than {TIMEOUT_SECONDS} seconds.")
#         except Exception as e:
#             print(f"❌ Error in run {i + 1}: {e}")


# if __name__ == "__main__":
#     if not BROWSERLESS_API_KEY:
#         print("❌ BROWSERLESS_API_KEY not found in environment variables.")
#         print("Please add BROWSERLESS_API_KEY=your_api_key to your .env file")
#         print("You can get a free API key from: https://www.browserless.io/")
#         exit(1)

#     print(
#         f"✅ Using Browserless endpoint: {BROWSERLESS_ENDPOINT.split('?')[0].replace('wss://', '')}")
#     print(f"🔑 API Key: {BROWSERLESS_API_KEY[:8]}...")
#     print("🔧 Using browser-use over CDP (remote Chromium).")

#     try:
#         asyncio.run(run_multiple_keys(1))
#     except KeyboardInterrupt:
#         print("\n🛑 Process interrupted by user.")
