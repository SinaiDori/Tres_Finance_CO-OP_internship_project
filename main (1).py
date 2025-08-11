import asyncio
import csv
from typing import Union
from dotenv import load_dotenv
from pydantic import BaseModel
from browser_use import Agent, Controller
from langchain_openai import ChatOpenAI
from temp_email import create_account, wait_for_email_with_link

# Use browser-use version 0.2.5, and not the same as etherscan

load_dotenv()

# Output format
class APIKey(BaseModel):
    api_key: str

controller = Controller(output_model=APIKey)
llm = ChatOpenAI(model="gpt-4o")


TIMEOUT_SECONDS = 180  # 3 minutes total

# Generating the keys using functions from temp_email.py
async def get_api() -> Union[str, None]:
    temp_email, token = create_account()
    print(f"📧 Temporary email: {temp_email}")
    password = "StrongPass123!"

    # Step 1: Sign up on Subscan
    signup_task = (
        f"You are creating a new account on Subscan. Follow these steps:\n"
        f"1. Open https://pro.subscan.io/signup/email\n"
        f"2. Fill in:\n"
        f"   - Email: {temp_email}\n"
        f"   - Password: {password}\n"
        f"   - Confirm Password: {password}\n"
        f"3. There is a checkbox below the 'Confirm Password' field and to the left of the text 'I have agree...'. Click that checkbox to agree to terms. Do not click on the label or link."
        f"4. Then click the 'Sign Up' button to submit the form.\n"
        f"Wait for the verification email after submitting."
    )

    await Agent(task=signup_task, llm=llm, controller=controller).run()
    print("✅ Signup submitted.")

    # Step 2: Wait for verification email (up to 100s)
    print("⏳ Waiting for confirmation email...")
    email_data = wait_for_email_with_link(token, timeout=10, interval=5)
    if not email_data or not email_data.get("link"):
        print("❌ No verification email received.")
        return None

    verification_link = email_data["link"]
    print(f"📨 Verification link: {verification_link}")
    # ✅ Sleep for 5 seconds before proceeding
    print("🕒 Waiting 10 seconds before visiting verification link...")
    await asyncio.sleep(10)
    await Agent(
        task=(
            f"Open the following verification link in your current tab:\n"
            f"{verification_link}\n"
        ),
        llm=llm,
        controller=controller
    ).run()
    print("✅ Account verified.")

    # Step 3: Login and create API key
    api_key_task = (
        f"You now need to log in and create an API key on Subscan:\n"
        f"1. Go to https://pro.subscan.io/login\n"
        f"2. Log in using:\n"
        f"   - Email: {temp_email}\n"
        f"   - Password: {password}\n"
        f"3. After login, click on the 'Products' section in the top menu.\n"
        f"4. Under 'Products', click on 'API Service'.\n"
        f"5. Click the 'Add' button to create a new key.\n"
        f"   - Enter 'Dana' as the app name and press 'create'.\n"
        f"6. Click the button to the left of the copy one to reveal the API token"
        f"7. Click the copy icon to copy the API key.\n"
        f"7. Return only the API key as JSON:\n"
        f"`api_key: <your_key_here>`"
    )
    agent = Agent(task=api_key_task, llm=llm, controller=controller)
    result = await agent.run()

    data = result.final_result()
    try:
        parsed = APIKey.model_validate_json(data)
        return parsed.api_key
    except Exception as e:
        print(f"⚠️ Failed to parse API key: {e}")
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
            else:
                print("⚠️ No key returned.")
        except asyncio.TimeoutError:
            print(f"⏰ Timeout: API generation run {i + 1} took longer than {TIMEOUT_SECONDS // 60} minutes.")


if __name__ == "__main__":
    try:
        asyncio.run(run_multiple_keys(1))
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user.")
