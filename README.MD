# Bernard Chatbot

Bernard is a GPT-based chatbot with the ability to run commands from the command line to start programs that have been set up in the environment variables.

We use the new GPT3.5 turbo 0613 function calls to parse responses in a way that allows for easy integration with Python code as function arguments.

## Prerequisites

Before running Bernard, make sure you have the following:

- Python 3.x installed on your system.
- An OpenAI API key to access the GPT3.5 turbo model.
- AWS Polly API credentials for text-to-speech functionality.

### OpenAI API Key

To obtain an OpenAI API key, follow these steps:

1. Sign in to your OpenAI account or create a new one at [OpenAI website](https://www.openai.com/).
2. Navigate to the API section and generate a new API key.
3. Copy the generated API key.

### AWS Polly API Credentials

To set up your AWS Polly API credentials as environment variables, follow these steps:

1. Sign in to the AWS Management Console or create a new account at [AWS website](https://aws.amazon.com/).
2. Open the IAM (Identity and Access Management) service.
3. Create or locate an IAM user with the necessary permissions for using the Polly service.
4. Obtain the Access Key ID and Secret Access Key for the IAM user.
5. Set the following environment variables:

```bash
AWS_ACCESS_KEY_ID=<your-access-key-id>
AWS_SECRET_ACCESS_KEY=<your-secret-access-key>
AWS_DEFAULT_REGION=<your-preferred-region>
```
## Getting Started

Clone the Bernard repository:

```
git clone https://github.com/OpenAyEye/Bernard.git
```

Navigate to the project directory:

```
cd Bernard
```

Install the required dependencies using pip:

```
pip install -r requirements.txt
```

Change config.txt to config.env file in the project directory and modify the following contents:

```
OpenAiKey="<your-openai-api-key>"
```

Replace `<your-openai-api-key>` with the API key you obtained from OpenAI.

Ensure that your AWS Polly API credentials are properly set as environment variables as mentioned earlier.

Run the Bernard chatbot:

```
python main.py
```

### Usage

Bernard listens for voice input via the microphone. Once started, Bernard will prompt you for input.
You can ask questions or provide instructions to Bernard.
If a command is recognized in your input, Bernard will execute it from the command line.

 - Bernard will only respond when addressed directly. "Bernard, what is the capital of New Mexico?" or, "how many planets are in our solar system, Bernard?"
 - To exit, tell Bernard you'd like to quit, exit, or end the program, etc. He's pretty smart, he'll usually know what you mean..

### Contributing

Contributions are welcome! If you find any issues or have suggestions for improvement, please feel free to submit a pull request.

### License
```
This project is licensed under the MIT License.
just give me a lil credit at the @openayeye handle :) thanks
```
