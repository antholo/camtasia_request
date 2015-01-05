# camtasia_request/forms.py

from flask_wtf import Form
from wtforms import TextField, RadioField, BooleanField
from datetime import date

class SetupForm(Form):
    # get OU and Course names from views
    # gets list of courses for selection
    baseCourse = RadioField('Select base course')
    
    # checkboxes for options
    embed = BooleanField("Would you like us to embed your videos on your course D2L homepage?")
    download = BooleanField(" Would you like to allow your students to be able to download your recordings?")
    share = BooleanField(" Would you like to allow your students to share your recordings?")
    training = BooleanField("Would you like some training?")

    # text field for recording location
    location = TextField("Recording location")

    # text field for course name - in case D2L provided coursename is unsatisfactory
    courseName = TextField("Course name as you would like it to appear")

    # text box for additional comments
    comments = TextAreaField("Any additional information you want to give us?")

    # select field for date after which files will not be needed on the server
    expiration = SelectField()