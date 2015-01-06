# camtasia_request/forms.py

from flask_wtf import Form
from wtforms import TextField, RadioField, BooleanField
from datetime import date

# month constants for expiration choices function
JAN = 1
SEP = 9
DEC = 12
FEB = 2
JUN = 6


class RequestForm(Form):
    # get OU and Course names from views
    # gets list of courses for selection
    course = RadioField('Select course',
        validators=[validators.required(message="You must select a course")])
    
    # checkboxes for options
    embed = BooleanField("Would you like us to embed your videos on your course D2L homepage?")
    download = BooleanField(" Would you like to allow your students to be able to download your recordings?")
    share = BooleanField(" Would you like to allow your students to share your recordings?")
    training = BooleanField("Would you like some training?")

    # text field for recording location
    location = TextField("Recording location")

    # text field for course name - in case D2L provided coursename is unsatisfactory
    courseName = TextField("Course name as you would like it to appear",
        validators=[validators.required(message="You must enter a course name")])

    # text box for additional comments
    comments = TextAreaField("Any additional information you want to give us?")

    # select field for date after which files will not be needed on the server
    expiration = SelectField(default='Do Not Delete', choices=get_expiration_choices())

    def get_expiration_choices():
    year = date.today().year
    month = date.today().month
    if month == JAN or (month >= SEP and month <= DEC):
        semester = 'Fall'
    elif month >= FEB and month <= JUN:
        semester = 'Spring'
    else: # month is between
        semester = 'Summer'
    choices = ['Do Not Delete', semester + " " + str(year)]
    while len(choices) < 10:
        if semester == 'Fall':
            year += 1
            semester = 'Spring'
        elif semester == 'Spring':
            semester = 'Summer'
        else: # semester == Summer
            semester = 'Fall'
        choices.append(semester + " " + str(year))
    return zip(choices, choices)