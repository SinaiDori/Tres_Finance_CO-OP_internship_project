import asyncio
import csv
from typing import Union
from dotenv import load_dotenv
from pydantic import BaseModel
from browser_use import Agent, Controller
from langchain_openai import ChatOpenAI
from temp_email_etherscan import create_account, wait_for_email_with_link

# Use browser-use version 0.1.45 only!

load_dotenv()

# Output format


class APIKey(BaseModel):
    api_key: str


controller = Controller(output_model=APIKey)
llm = ChatOpenAI(model="gpt-4o")

# To prevent endless-loops
TIMEOUT_SECONDS = 300  # 5 minutes


# Generating the keys using functions from temp_email.py
async def get_api() -> Union[str, None]:
    temp_email, token = create_account()
    print(f"📧 Temporary email: {temp_email}")
    username = temp_email.split("@")[0]
    password = "StrongPass123!"

    # 1. Sign-up
    signup_task = (
        f"Go to https://etherscan.io/register and sign up using these values:\n"
        f"- Username: {username}\n"
        f"- Email: {temp_email}\n"
        f"- Confirm Email: {temp_email}\n"
        f"- Password: {password}\n"
        f"- Confirm Password: {password}\n"
        "Check the 'I agree to the Terms and Conditions' box and click 'Create an Account'.\n"
        "After submission, confirm that the page says the account is pending email verification."
    )
    await Agent(task=signup_task, llm=llm, controller=controller).run()
    print("✅ Signup submitted.")

    # 2. Email verification
    print("⏳ Waiting for confirmation email...")
    email_data = wait_for_email_with_link(token, timeout=10)
    if not email_data or not email_data.get("link"):
        print("❌ No verification email received.")
        return None

    verification_link = email_data["link"]
    print(f"📨 Verification link: {verification_link}")
    await Agent(
        task=f"Open this link to complete email verification: {verification_link}. If a confirmation button appears, click it.",
        llm=llm,
        controller=controller,
    ).run()
    print("✅ Account verified.")

    # 3. Login + get API key
    api_key_task = (
        f"Go to https://etherscan.io/login and sign in using the following credentials:\n"
        f"- Username: {username}\n"
        f"- Password: {password}\n"
        f"After logging in, navigate to 'API Dashboard', click '+ Add', name it 'Dana', and submit.\n"
        f"Return the key as:\n"
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


def write_csv(api_key: str, filename="api_keys.csv") -> None:
    with open(filename, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([api_key])
    print(f"✅ API key saved to '{filename}'.")

# Running the script in a loop


async def run_multiple_keys(n: int = 5):
    for i in range(n):
        print(f"\n🔁 Starting run {i + 1} of {n}")
        try:
            key = await asyncio.wait_for(get_api(), timeout=TIMEOUT_SECONDS)
            if key:
                write_csv(key)
            else:
                print("⚠️ No key returned.")
        except asyncio.TimeoutError:
            print(
                f"⏰ Timeout: API generation run {i + 1} took longer than {TIMEOUT_SECONDS // 60} minutes.")

if __name__ == "__main__":
    try:
        asyncio.run(run_multiple_keys(5))
    except KeyboardInterrupt:
        print("🛑 Interrupted by user.")
