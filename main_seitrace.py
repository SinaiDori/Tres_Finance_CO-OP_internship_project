import asyncio
import csv
from typing import Optional, Union
from dotenv import load_dotenv
from pydantic import BaseModel
from browser_use import Agent, Controller
from browser_use.agent.views import ActionResult
from langchain_openai import ChatOpenAI
from temp_email_seitrace import create_account, wait_for_verification_code

# Use browser-use version 0.2.5, and not the same as etherscan

load_dotenv()


class APIKey(BaseModel):
    api_key: str


TIMEOUT_SECONDS = 180  # Timeout for each full flow

# Generating the keys using functions from temp_email.py


async def get_api() -> Union[str, None]:
    email, token = create_account()
    print(f"📧 Temporary email: {email}")
    password = "Strong!Pass123"
    username = email.split("@")[0]

    controller = Controller(
        output_model=APIKey,
    )
    llm = ChatOpenAI(model="gpt-4o")

    def read_otp_from_mailbox() -> ActionResult:
        code = wait_for_verification_code(token)
        return ActionResult(
            extracted_content=code,
            description=f"Fetched OTP Code from mailbox: {code}"
        )

    controller.action("Read OTP from mailbox")(read_otp_from_mailbox)

    task = (
        f"1. Search for seitrace in Gooogle and enter that website .\n"
        f"2. Click 'Sign In' → 'Register'.\n"
        f"3. Enter email {email} and click 'Create account'.\n"
        f"4. Use the action 'Read OTP from mailbox' to get the OTP code.\n"
        f"5. Enter the code when prompted, set password to {password}, and finish registration.\n"
        f"6. Go to Profile → API Keys → Add API Key.\n"
        f"7. Use name 'dana'.\n"
        f"8. Copy the new API key and return it .\n"
    )

    agent = Agent(task=task, llm=llm, controller=controller)
    result = await agent.run()

    data = result.final_result()
    try:
        parsed = APIKey.model_validate_json(data)
        return parsed.api_key
    except Exception as e:
        print(f"⚠️ Failed to parse API key: {e}")
        return None

# Writing the api key to csv


def write_csv(api_key: str, filename="seitrace_api_keys.csv") -> None:
    with open(filename, "a", newline="") as file:
        writer = csv.writer(file)
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
            print(
                f"⏰ Timeout: API generation run {i + 1} took longer than {TIMEOUT_SECONDS // 60} minutes.")

if __name__ == "__main__":
    try:
        asyncio.run(run_multiple_keys(3))
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user.")
