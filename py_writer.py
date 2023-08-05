import os
import subprocess
import openai
from dotenv import load_dotenv
import json
# Load environment variables from the .env file
load_dotenv("config.env")

# Access the OpenAI key from the environment variable
openai.api_key = os.environ.get("OpenAiKey")

functions = [
    {
        "name": "source_writer",
        "description": "generates python source code wrapped in triple single quotes.",
        "parameters": {
            "type": "object",
            "properties": {
                "source_code": {
                    "type": "string",
                    "description": "generated source code wrapped in triple single quotes to preserve formatting."
                }
            }
        }
    }
]

def write_code(user_input):

    import re
    print(f"User input: {user_input}")
    print("Writing that Code!!")
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k-0613",
        messages=[
            {
                "role": "system",
                "content": "You are a useful command line assistant."
            },
            {
                "role": "user",
                #"content": f"Generate the following Python source code wrapped in triple single quotes: {user_input}.  If the prompt has source code with output and errors present, please handle any error codes and present the updated script in it's entirety. You will either be generating completely new code, or error handling code provided. It's important to make sure the response is wrapped in ''' to preserve formatting, and to provide the complete script because there won't be any human intervention to make the changes to the script. Only provide the source code, wrapped in ''' to preserve the formatting as a multi-line python string. never user full quotation marks.""content": f"Generate the following Python source code wrapped in triple single quotes: {user_input}.  If the prompt has source code with output and errors present, please handle any error codes and present the updated script in it's entirety. You will either be generating completely new code, or error handling code provided. It's important to make sure the response is wrapped in ''' to preserve formatting, and to provide the complete script because there won't be any human intervention to make the changes to the script. Only provide the source code, wrapped in ''' to preserve the formatting as a multi-line python string. never user full quotation marks."
                "content": f"use the following prompt to generate python source code in the form of a multi-line string {user_input}.  Make sure to provide complete scripts with full logic, this process will be automated, there won't be human intervention in the code writing process. never generate double quotes '"' absolutely do not do that, ever. Your responses are returned in json format and double quotes crash everything. To reiterate, do not generate any '"' double quotations"
            }
        ],
        functions=functions,
        function_call={
            "name": functions[0]["name"]
        },
        max_tokens=10000
    )
    arguments = response["choices"][0]["message"]["function_call"]["arguments"]

    print(f"before removing triple quotes from arguments \n {arguments[0]}")
    #arguments = re.sub(r'"""(.*?)"""', r"'''\1'''", arguments)
    print(f"After removing quotations marks from arguments\n {arguments}")
    json_obj = json.loads(arguments)
    print("Source Code Generated: ")
    print(json_obj["source_code"])
    print("###########################################################################################################")
    return json_obj["source_code"]
    #return arguments

def run_script(script_location):
    output = ""
    while True:
        with open(script_location, 'r') as file:
            content = f"{file.read()}"
        command = ["python", f"{script_location}"]

        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)

            print("Output of the new script:")
            print(output)
            lines = output.strip().split('\n')
            for line in lines:
                print("Line:", line)
            break  # If the script runs successfully, break the loop

        except subprocess.CalledProcessError as e:
            print("Error:", e.output)  # Print the error output if the command fails
            print("")
            print("Re-Writing Script")
            content = content + e.output
            rewrite = write_code(content)
            with open(script_location, 'w') as file:
                file.write(rewrite)
            print("Script re-written, trying again! ")
            continue  # If an error occurs, continue the loop to try again
    print("Success! :)")
    return output

def run_script_bak(script_location):
    with open(script_location, 'r') as file:
        content = f"{file.read()}"
    command = ["python", f"{script_location}"]

    # Run the command and capture the output
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
        # Now the 'output' variable contains the output of the other script
        print("Output of the other script:")
        print(output)

        # You can further process the output or use it as needed
        # For example, splitting it into lines:
        lines = output.strip().split('\n')
        for line in lines:
            print("Line:", line)


    except subprocess.CalledProcessError as e:
        print("Error:", e.output)  # Print the error output if the command fails
        content = content + e.output
        print("")
        print("re-writing script")
        rewrite = write_code(content)
        with open(script_location, 'w') as file:
            file.write(rewrite)
        print("script re-writen, trying again")

def main(source_code, title):
    # Create the 'source_code' directory if it doesn't exist
    if not os.path.exists('source_code'):
        os.makedirs('source_code')

    # Generate a unique name for the source code file
    source_code_name = f'{title}.py'

    # Save the source code to the file
    source_code_file_path = os.path.join('source_code', source_code_name)
    with open(source_code_file_path, 'w') as file:
        file.write(source_code)

    print(f"Source code saved to: {source_code_file_path}")
    print("")
    print("Attempting to run script: ")
    print("")
    run_script(source_code_file_path)

# Example usage
if __name__ == "__main__":
    #user_input = "write a python script that generates a simple web page with a title, a header, and some content. have the user enter these variables via input() if there are any dependencies needed include a function to install them via subprocess call to pip and a call to that install function at the start of the script."
    user_input = "write a breakout clone in python, it should be complete, with a controllable 'character' bar that moves left to right with a and d respectively on the keyboard, there should be a ball that bounces around the screen and breaks blocks at the top of the screen when it collides with them. the blocks should be worth points, when all the blocks break the level is over."
    source_code = write_code(user_input)
    source_code = source_code[2:-2]
    main(source_code, title="boggle")