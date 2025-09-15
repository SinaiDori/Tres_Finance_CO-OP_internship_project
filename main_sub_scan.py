# import asyncio
# import csv
# import os
# import subprocess
# from pathlib import Path
# from typing import Union

# from dotenv import load_dotenv
# from pydantic import BaseModel
# from browser_use import Agent, Controller
# from browser_use.agent.views import ActionResult
# from langchain_openai import ChatOpenAI
# from temp_email_sub_scan import create_account, wait_for_email_with_link

# # Use browser-use version 0.1.45
# load_dotenv()

# # ---------- Output model ----------


# class APIKey(BaseModel):
#     api_key: str


# # ---------- LLM & controller (reuse across runs) ----------
# controller = Controller(output_model=APIKey)
# llm = ChatOpenAI(model="gpt-4o")

# # ---------- Global variable to store agent reference ----------
# current_agent = None

# # ---------- Timeouts ----------
# TIMEOUT_SECONDS = 1000  # keep as you set; adjust if needed

# # ---------- Cleanup helpers ----------
# PROFILE_DIR = Path.home() / ".config" / "browseruse" / "profiles" / "default"


# def _pkill(pattern: str) -> None:
#     """Best-effort kill by pattern (Linux/GitHub Actions friendly)."""
#     try:
#         subprocess.run(["pkill", "-f", pattern], check=False)
#     except FileNotFoundError:
#         pass
#     except Exception:
#         pass


# def cleanup_chrome_profile() -> None:
#     """Kill lingering Chromium/Chrome and remove profile lock files."""
#     for pat in (
#         "chrome-linux/chrome",
#         "Chromium",
#         "chrome --type",
#         "playwright",
#     ):
#         _pkill(pat)
#     try:
#         if PROFILE_DIR.exists():
#             for p in PROFILE_DIR.glob("Singleton*"):
#                 try:
#                     p.unlink()
#                 except Exception:
#                     pass
#     except Exception:
#         pass

# # ---------- Core run ----------


# async def get_api() -> Union[str, None]:
#     global current_agent

#     temp_email, token = create_account()
#     print(f"📧 Temporary email: {temp_email}")
#     password = "StrongPass123!"

#     def get_verification_link_from_mailbox():
#         link = wait_for_email_with_link(token)
#         if link:
#             return ActionResult(
#                 extracted_content=f"VERIFICATION_LINK: {link}",
#                 description=f"✅ Successfully fetched verification link: {link}"
#             )
#         else:
#             return ActionResult(
#                 extracted_content="NO_LINK_FOUND",
#                 description="❌ Failed to fetch verification link from mailbox"
#             )

#     async def check_terms_checkbox():
#         global current_agent

#         try:
#             page = None

#             # Method 1: Access through browser_context
#             if current_agent and hasattr(current_agent, 'browser_context'):
#                 context = current_agent.browser_context
#                 if context and hasattr(context, 'pages') and len(context.pages) > 0:
#                     page = context.pages[0]
#                     print("✅ Found page via browser_context.pages[0]")

#             # Method 2: Access through playwright_browser
#             if not page and current_agent and hasattr(current_agent, 'browser'):
#                 browser = current_agent.browser
#                 if hasattr(browser, 'playwright_browser'):
#                     playwright_browser = browser.playwright_browser
#                     if playwright_browser and hasattr(playwright_browser, 'contexts') and len(playwright_browser.contexts) > 0:
#                         context = playwright_browser.contexts[0]
#                         if hasattr(context, 'pages') and len(context.pages) > 0:
#                             page = context.pages[0]
#                             print(
#                                 "✅ Found page via playwright_browser.contexts[0].pages[0]")

#             # Method 3: Direct access through context
#             if not page and current_agent and hasattr(current_agent, 'context'):
#                 context = current_agent.context
#                 if context and hasattr(context, 'pages') and len(context.pages) > 0:
#                     page = context.pages[0]
#                     print("✅ Found page via context.pages[0]")

#             if page:
#                 print("🎯 Executing JavaScript to click checkbox...")
#                 result = await page.evaluate("""
#                     (() => {
#                         console.log('JavaScript executing...');
#                         const checkbox = document.querySelector('img[src*="icon_unchecked"]');
#                         console.log('Checkbox found:', checkbox);
#                         if (checkbox) {
#                             checkbox.click();
#                             console.log('Checkbox clicked successfully');
#                             return 'SUCCESS: Checkbox clicked';
#                         }
#                         console.log('Checkbox not found');
#                         return 'ERROR: Checkbox not found';
#                     })()
#                 """)

#                 print(f"📝 JavaScript result: {result}")

#                 return ActionResult(
#                     extracted_content="CHECKBOX_CLICKED",
#                     description=f"✅ Auto-clicked terms checkbox: {result}"
#                 )
#             else:
#                 print("❌ Could not find page object")

#         except Exception as e:
#             print(f"❌ Error in auto-click: {e}")
#             import traceback
#             traceback.print_exc()

#         return ActionResult(
#             extracted_content="MANUAL_CLICK_NEEDED",
#             description="❌ Auto-click failed - checkbox must be clicked manually"
#         )

#     # Register the actions
#     controller.action("Fetch verification link from mailbox")(
#         get_verification_link_from_mailbox)
#     controller.action("Auto-check terms agreement")(check_terms_checkbox)

#     try:
#         # Step 1: Sign up on Subscan
#         signup_task = (
#             f"You are creating a new account on Subscan. Follow these steps:\n"
#             f"1. Open https://pro.subscan.io/signup/email\n"
#             f"2. Complete the Sign-Up:\n"
#             f"   Under 'Email' enter: {temp_email}\n"
#             f"   Under 'Password' enter: {password}\n"
#             f"   Under 'Confirm Password' enter: {password}\n"
#             f"3. Execute the 'Auto-check terms agreement' action (this will automatically check the terms box).\n"
#             f"4. If the auto-check failed, manually click the image with 'icon_unchecked' in its source.\n"
#             f"5. Wait 2 seconds.\n"
#             f"6. Then click the 'Sign Up' button to submit the form.\n"
#             f"7. Click on the 'Products' section in the top menu.\n"
#             f"8. Under 'Products', click on 'API Service'.\n"
#             f"9. If you see a verification prompt or message, look for a 'Resend Email' button and click it. Then wait 10 seconds."
#             f"(DO NOT wait 2 minutes even if the webpage suggests it.\n"
#             f"10. Execute the 'Fetch verification link from mailbox' action. Then wait 10 seconds.\n"
#             f"11. Open the link you fetched\n"
#             f"12. Click on the 'Products' section in the top menu.\n"
#             f"13. Under 'Products', click on 'API Service'.\n"
#             f"14. Click on 'API Key'.\n"
#             f"15. Enter 'Sinai' as the app name.\n"
#             f"16. Click 'Create New API Key'.\n"
#             f"17. Click the small button to the left of the copy API token one to reveal the API token (so it will be without *************). "
#             f"The icon of this button is a closed eye icon (that means that the API Key Token is hidden).\n"
#             f"18. Only after the last stage, click the small copy icon to copy the API key.\n"
#             f"19. If the API Key you copied has asterisks in it - return to step 17. If not - continue to the next step.\n"
#             f"20. Return only the API key as JSON:\n"
#             f'{{"api_key": "<your_key_here>"}}'
#         )

#         # Create agent and store reference
#         current_agent = Agent(task=signup_task, llm=llm,
#                               controller=controller)
#         result = await current_agent.run()

#         data = result.final_result()
#         try:
#             parsed = APIKey.model_validate_json(data)
#             return parsed.api_key
#         except Exception as e:
#             print(f"⚠️ Failed to parse API key: {e}")
#             print(f"Raw result: {data}")
#             return None

#     finally:
#         # Clean shutdown of the browser/session + profile unlock
#         current_agent = None  # Clear the reference
#         cleanup_chrome_profile()

# # ---------- CSV writer ----------


# def write_csv(api_key: str, filename="sub_scan_api_keys.csv") -> None:
#     with open(filename, "a", newline="") as csvfile:
#         writer = csv.writer(csvfile)
#         writer.writerow([api_key])
#     print(f"✅ API key saved to '{filename}'.")

# # ---------- Loop ----------


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
#             mins = TIMEOUT_SECONDS // 60
#             print(
#                 f"⏰ Timeout: API generation run {i + 1} exceeded {mins} minutes.")
#         except Exception as e:
#             print(f"❌ Error in run {i + 1}: {e}")
#         finally:
#             # Safety cleanup after each iteration + a short breather
#             cleanup_chrome_profile()
#             await asyncio.sleep(1.0)

# if __name__ == "__main__":
#     try:
#         asyncio.run(run_multiple_keys(1))
#     except KeyboardInterrupt:
#         print("\n🛑 Process interrupted by user.")


# Disable telemetry BEFORE any other imports
from temp_email_sub_scan import create_account, wait_for_email_with_link
from langchain_openai import ChatOpenAI
from browser_use.agent.views import ActionResult
from browser_use import Agent, Controller
from pydantic import BaseModel
from dotenv import load_dotenv
import contextlib
from typing import Union
from pathlib import Path
import urllib3
import requests
import subprocess
import csv
import asyncio
import os
import sys

# Multiple ways to disable telemetry to ensure it works
os.environ['BROWSER_USE_TELEMETRY'] = 'false'
os.environ['BROWSER_USE_DISABLE_TELEMETRY'] = 'true'
os.environ['DISABLE_TELEMETRY'] = 'true'
os.environ['DO_NOT_TRACK'] = '1'

# Disable SSL verification for PostHog if telemetry still runs
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''

print("🚫 Telemetry disabled, SSL verification disabled for analytics")


# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Use browser-use version 0.1.45
load_dotenv()

# ---------- Output model ----------


class APIKey(BaseModel):
    api_key: str

# ---------- Enhanced proxy testing and configuration ----------


def test_scraperapi_connectivity():
    """Test ScraperAPI service connectivity without proxy first"""
    scraperapi_key = os.getenv('SCRAPERAPI_KEY')
    if not scraperapi_key:
        print("❌ No SCRAPERAPI_KEY found")
        return False

    try:
        # Test ScraperAPI service directly first
        url = f"https://api.scraperapi.com/?api_key={scraperapi_key}&url=http://httpbin.org/ip"
        response = requests.get(url, timeout=30, verify=False)

        if response.status_code == 200:
            print("✅ ScraperAPI service is accessible")
            return True
        else:
            print(f"❌ ScraperAPI service returned: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ ScraperAPI service test failed: {e}")
        return False


def test_proxy_configuration(proxy_url, test_url="http://httpbin.org/ip"):
    """Test a specific proxy configuration"""
    try:
        print(f"🧪 Testing proxy: {proxy_url[:50]}...")

        # Configure proxy for requests
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }

        # Test with requests library
        response = requests.get(
            test_url,
            proxies=proxies,
            timeout=30,
            verify=False,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )

        if response.status_code == 200:
            try:
                data = response.json()
                ip = data.get('origin', 'unknown')
                print(f"✅ Proxy works! IP: {ip}")
                return True
            except:
                print(f"✅ Proxy works! Status: {response.status_code}")
                return True
        else:
            print(f"❌ Proxy failed with status: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Proxy test failed: {e}")
        return False


def get_working_proxy():
    """Find a working ScraperAPI proxy configuration"""
    scraperapi_key = os.getenv('SCRAPERAPI_KEY')
    if not scraperapi_key:
        print("❌ No SCRAPERAPI_KEY found")
        return None

    # Test ScraperAPI service connectivity first
    if not test_scraperapi_connectivity():
        print("❌ ScraperAPI service is not accessible")
        return None

    print("🔍 Testing different proxy authentication formats...")

    # Different authentication formats to try
    proxy_formats = [
        # Format 1: Basic username:password
        f"http://scraperapi:{scraperapi_key}@proxy-server.scraperapi.com:8001",

        # Format 2: Username with session parameter
        f"http://scraperapi-session-123:{scraperapi_key}@proxy-server.scraperapi.com:8001",

        # Format 3: Premium parameter in username
        f"http://scraperapi.premium=true:{scraperapi_key}@proxy-server.scraperapi.com:8001",

        # Format 4: Country and premium in username
        f"http://scraperapi.premium=true.country_code=US:{scraperapi_key}@proxy-server.scraperapi.com:8001",

        # Format 5: Alternative port
        f"http://scraperapi:{scraperapi_key}@proxy-server.scraperapi.com:8000",
    ]

    for i, proxy_url in enumerate(proxy_formats, 1):
        print(f"\n🧪 Testing format {i}/{len(proxy_formats)}:")
        if test_proxy_configuration(proxy_url):
            print(f"✅ Found working proxy format: {i}")
            return proxy_url

    print("❌ No working proxy configuration found")
    return None


@contextlib.contextmanager
def scraperapi_proxy():
    """Context manager to enable ScraperAPI proxy only when needed"""
    working_proxy = get_working_proxy()

    if not working_proxy:
        print("⚠️ No working proxy found - running without proxy")
        yield
        return

    # Store original proxy settings
    original_proxies = {}
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY']:
        original_proxies[key] = os.environ.get(key)

    try:
        # Set working proxy
        os.environ['HTTP_PROXY'] = working_proxy
        os.environ['HTTPS_PROXY'] = working_proxy

        # Comprehensive bypass list
        no_proxy_domains = [
            'localhost',
            '127.0.0.1',
            '*.local',
            'posthog.com',
            '*.posthog.com',
            'eu.i.posthog.com',
            'us.i.posthog.com',
            'api.mail.tm',
            'powerscrews.com',
            '*.powerscrews.com',
            'openai.com',
            '*.openai.com'
        ]
        os.environ['NO_PROXY'] = ','.join(no_proxy_domains)

        print(f"🌐 Proxy enabled successfully")
        print(f"🚫 Bypassing proxy for: {len(no_proxy_domains)} domains")
        yield

    finally:
        # Restore original proxy settings
        for key, value in original_proxies.items():
            if value is None:
                if key in os.environ:
                    del os.environ[key]
            else:
                os.environ[key] = value
        print("🔄 Proxy settings restored")


# ---------- LLM & controller (reuse across runs) ----------
controller = Controller(output_model=APIKey)
llm = ChatOpenAI(model="gpt-4o")

# ---------- Global variable to store agent reference ----------
current_agent = None

# ---------- Timeouts ----------
TIMEOUT_SECONDS = 1000

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
    global current_agent

    # Step 1: Create temp email WITHOUT proxy
    print("📧 Creating temporary email (without proxy)...")
    temp_email, token = create_account()
    print(f"📧 Temporary email: {temp_email}")
    password = "StrongPass123!"

    def get_verification_link_from_mailbox():
        print("📧 Fetching verification link (without proxy)...")
        link = wait_for_email_with_link(token)
        if link:
            return ActionResult(
                extracted_content=f"VERIFICATION_LINK: {link}",
                description=f"✅ Successfully fetched verification link: {link}"
            )
        else:
            return ActionResult(
                extracted_content="NO_LINK_FOUND",
                description="❌ Failed to fetch verification link from mailbox"
            )

    async def check_terms_checkbox():
        global current_agent
        try:
            page = None
            if current_agent and hasattr(current_agent, 'browser_context'):
                context = current_agent.browser_context
                if context and hasattr(context, 'pages') and len(context.pages) > 0:
                    page = context.pages[0]

            if page:
                print("🎯 Executing JavaScript to click checkbox...")
                result = await page.evaluate("""
                    (() => {
                        const checkbox = document.querySelector('img[src*="icon_unchecked"]');
                        if (checkbox) {
                            checkbox.click();
                            return 'SUCCESS: Checkbox clicked';
                        }
                        return 'ERROR: Checkbox not found';
                    })()
                """)
                return ActionResult(
                    extracted_content="CHECKBOX_CLICKED",
                    description=f"✅ Auto-clicked terms checkbox: {result}"
                )
        except Exception as e:
            print(f"❌ Error in auto-click: {e}")

        return ActionResult(
            extracted_content="MANUAL_CLICK_NEEDED",
            description="❌ Auto-click failed - checkbox must be clicked manually"
        )

    # Register the actions
    controller.action("Fetch verification link from mailbox")(
        get_verification_link_from_mailbox)
    controller.action("Auto-check terms agreement")(check_terms_checkbox)

    signup_task = (
        f"You are creating a new account on Subscan. Follow these steps:\n"
        f"1. Open https://pro.subscan.io/signup/email\n"
        f"2. Complete the Sign-Up:\n"
        f"   Under 'Email' enter: {temp_email}\n"
        f"   Under 'Password' enter: {password}\n"
        f"   Under 'Confirm Password' enter: {password}\n"
        f"3. Execute the 'Auto-check terms agreement' action (this will automatically check the terms box).\n"
        f"4. If the auto-check failed, manually click the image with 'icon_unchecked' in its source.\n"
        f"5. Wait 2 seconds.\n"
        f"6. Then click the 'Sign Up' button to submit the form.\n"
        f"7. Click on the 'Products' section in the top menu.\n"
        f"8. Under 'Products', click on 'API Service'.\n"
        f"9. If you see a verification prompt or message, look for a 'Resend Email' button and click it. Then wait 10 seconds."
        f"(DO NOT wait 2 minutes even if the webpage suggests it.\n"
        f"10. Execute the 'Fetch verification link from mailbox' action. Then wait 10 seconds.\n"
        f"11. Open the link you fetched\n"
        f"12. Click on the 'Products' section in the top menu.\n"
        f"13. Under 'Products', click on 'API Service'.\n"
        f"14. Click on 'API Key'.\n"
        f"15. Enter 'Sinai' as the app name.\n"
        f"16. Click 'Create New API Key'.\n"
        f"17. Click the small button to the left of the copy API token one to reveal the API token (so it will be without *************). "
        f"The icon of this button is a closed eye icon (that means that the API Key Token is hidden).\n"
        f"18. Only after the last stage, click the small copy icon to copy the API key.\n"
        f"19. If the API Key you copied has asterisks in it - return to step 17. If not - continue to the next step.\n"
        f"20. Return only the API key as JSON:\n"
        f'{{"api_key": "<your_key_here>"}}'
    )

    # Try with proxy first, but with better error handling
    print("\n🌐 Attempting with ScraperAPI proxy...")
    try:
        with scraperapi_proxy():
            current_agent = Agent(
                task=signup_task, llm=llm, controller=controller)
            result = await current_agent.run()
            data = result.final_result()

            if data:
                try:
                    parsed = APIKey.model_validate_json(data)
                    print("✅ Success with proxy!")
                    return parsed.api_key
                except Exception as e:
                    print(f"⚠️ Failed to parse result with proxy: {e}")

    except Exception as e:
        print(f"❌ Proxy attempt failed: {e}")

    finally:
        current_agent = None
        cleanup_chrome_profile()

    # Fallback without proxy
    print("\n🔄 Attempting WITHOUT proxy as fallback...")
    try:
        current_agent = Agent(task=signup_task, llm=llm, controller=controller)
        result = await current_agent.run()
        data = result.final_result()

        if data:
            try:
                parsed = APIKey.model_validate_json(data)
                print("✅ Success without proxy!")
                return parsed.api_key
            except Exception as e:
                print(f"⚠️ Failed to parse result without proxy: {e}")

    except Exception as e:
        print(f"❌ Fallback attempt failed: {e}")

    finally:
        current_agent = None
        cleanup_chrome_profile()

    return None

# ---------- CSV writer ----------


def write_csv(api_key: str, filename="sub_scan_api_keys.csv") -> None:
    with open(filename, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([api_key])
    print(f"✅ API key saved to '{filename}'.")

# ---------- Loop ----------


async def run_multiple_keys(n: int = 1):
    for i in range(n):
        print(f"\n🔄 Starting run {i + 1} of {n}")
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
            cleanup_chrome_profile()
            await asyncio.sleep(1.0)

if __name__ == "__main__":
    try:
        asyncio.run(run_multiple_keys(1))
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user.")
