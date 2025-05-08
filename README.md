# JobMatch - Tinder for Jobs

A job matching application that connects job seekers and recruiters using a Tinder-like swiping interface.

## Features

- **User Types**:
  - Job Seekers (candidates)
  - Job Givers (recruiters)
  - Admin

- **Core Functionality**:
  - Tinder-like swiping interface
  - Profile creation for job seekers and recruiters
  - CV upload for job seekers
  - Job posting for recruiters
  - Matching system when both parties swipe right
  - Credit system for monetization

## Technology Stack

- **Backend**: Python
- **Frontend**: Streamlit
- **Database**: PostgreSQL

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/jobmatch.git
   cd jobmatch
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Configure the database:
   - Copy `.env.example` to `.env`
   - Update the database credentials in `.env`

5. Run the application:
   ```
   streamlit run app.py
   ```

## Usage

### For Job Seekers

1. Create an account as a Job Seeker
2. Complete your profile and upload your CV
3. Swipe right on jobs you're interested in
4. When there's a match, you'll earn credits
5. Redeem credits once you accumulate 100

### For Recruiters

1. Create an account as a Job Giver
2. Complete your company profile
3. Purchase credits to post jobs
4. Post job listings
5. Swipe right on candidates you're interested in
6. When there's a match, you'll be able to view the candidate's full profile and CV

### For Admin

1. Login with admin credentials
2. Manage users and job listings
3. View platform statistics
4. Process credit transactions

## Project Structure

```
jobmatch/
├── app/
│   ├── database/
│   │   └── connection.py
│   ├── models/
│   │   ├── user.py
│   │   ├── job_seeker.py
│   │   ├── job_giver.py
│   │   ├── job.py
│   │   ├── swipe.py
│   │   └── match.py
│   ├── frontend/
│   │   ├── auth.py
│   │   ├── admin.py
│   │   ├── job_seeker.py
│   │   └── job_giver.py
│   └── utils/
│       └── file_handler.py
├── uploads/
│   └── cvs/
├── app.py
├── requirements.txt
├── .env.example
└── README.md
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Inspired by Tinder's swiping interface
- Built with Streamlit for rapid development
- PostgreSQL for robust data storage