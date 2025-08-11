import asyncio
import csv
from typing import Union
from dotenv import load_dotenv
from pydantic import BaseModel
from browser_use import Agent, Controller
from langchain_openai import ChatOpenAI
from temp_email_sub_scan import create_account, wait_for_email_with_link

# Use browser-use version 0.2.5, and not the same as etherscan

load_dotenv()

# Output format


class APIKey(BaseModel):
    api_key: str


controller = Controller(output_model=APIKey)
llm = ChatOpenAI(model="gpt-4o")

TIMEOUT_SECONDS = 300  # 5 minutes total

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

    await Agent(task=signup_task, llm=llm, controller=controller).run()
    print("✅ Signup submitted.")

    # Step 2: Wait for verification email (up to 5 minutes)
    print("⏳ Waiting for verification email...")
    email_data = wait_for_email_with_link(token, timeout=300, interval=10)
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
                  llm=llm, controller=controller)
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
        asyncio.run(run_multiple_keys(1))
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user.")
