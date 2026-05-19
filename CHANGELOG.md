## v1.13.0

- Added biology questions page

## v1.12.3

- Removing obrigatory billing addres
- [

## v1.12.2

- Fixed forgot password route

## v1.12.1

- Changed the lenguage of the checkout to espanish

## v1.12.0

- Changes on checkout generation to improve the reliability of the payments
- Runned black formater to improve code quality

## v1.11.2

- Adding a setting on checkout to not add extra charges after payment

## v1.11.1

- Added front deploy url to the cors origins

## v1.11.0

- Changed the payment format from signature to package
- Now the route /question-answers/last-answers don't need an active payment to be used, only a valid token

## v1.10.1

- Added a ENV Variable to remove documentation routes

## v1.10.0

- Added email sender module
- Added Forgot Password and Reset Password route

## v1.9.0

- Added user_feedback table
- Added POST and  GET All routes for user_feedback table
- Added a validation to the user creation for passwords to force the user to create a reliable password

## v1.8.1

- Fixed answer questions GET route to send just questions that was answered by the user
- Added permission to this route

## v1.8.0

- Added question generation limit
- Added the counter return on login
- Counter managment using stripe events

## v1.7.0

- Added Payment logic
- Implemented subscription managment using stripe webhooks
- Created a subscriptions table
- Adjustments on Login route and permissions logic

## v1.6.12

- Changed the prompt logic to improve the questions quality

## v1.6.11

- Increasing the quality of the prompt

## v1.6.10

- Increasing the quality of the prompt

## v1.6.9

- Increasing the quality of the prompt

## v1.6.8

- Changes on anatomy prompt to improve the question generation

## v1.6.7

- Adjustments and validations to the subtopic list to improve the questions quality

## v1.6.6

- Added subtopics description to the questions and to the prompt
- Increased the quality of promtp improving rules

## v1.6.5

- Removed last update of the question prompt, it breaked the question generation

## v1.6.4

- Added rules to the topic, subtopic and diversity mode to improve the question generation and control the question content

## v1.6.3

- Increase the quality of answers
- Added a rule to send just one correct answers with hard thinking answer process
- Improvments on random choice selection

## v1.6.2

- Added random letter correct answer to remove 'only A correct answer cicle'

## v1.6.1

- Removed 'musculos_abdomen' from Locomotor to Splacno

## v1.6.0

- Added subtopic parameter to the AI Prompt
- Added subtopic parameter to the questions table
- Changed subject to diversity_mode to improve compatibility
- Added a list of subtopics generated from bibliography references
- Added a migration script to deploy database

## v1.5.1

- Fixing uncompatible questions generation
- Changing question validation schema to send english words
- Increasing compatibility and questions quality

## v1.5.0

- Changed Cookies token validation to Header token validation (Authorization)

## v1.4.0

- Fixed token Cookies authentication
- Increased the quality of question generation prompt
- Added a Logout route
- Added GET and GET by ID route for institutions

## v1.3.1

- Added response models to POST /users, GET /question-answers/latest-answers and POST /anatomy/ai

## v1.3.0

- Changed JWT send format (Coockies instead Request Headers)
- Adjusted login route

## v1.2.0

- Added question answers route
- Added questions GET joinig answers filtering per user

## v1.1.0

- Added UBA institution and students profile
- Added account creation route

## v1.0.0

- JWT Validation
- Permission validation
- Account creation

## v0.3.0

- Created files to generate a new version for Database (Migrations)

## v0.2.1

- Added Railsway deploy files

## v0.2.0

- Now, All questions generated are being saved on questions table
- Fixed CORS parameters and middlewares configurations
- Commented subject feature

## v0.1.0

- Setup the Users, Questions, Authentication, Profiles and Healthy routes
- Added Fernet encryptation and JWT token generation
- Created DB scripts
- Added JWT Middleware











