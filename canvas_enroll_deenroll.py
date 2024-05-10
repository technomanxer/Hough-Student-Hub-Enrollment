from functools import partial
import json
from canvasapi import Canvas, user
from canvasapi.exceptions import CanvasException
import csv, os
from tqdm import tqdm
from tqdm.contrib.concurrent import thread_map

#API Keys from JSON object
with open(os.path.dirname(os.getcwd()) + '/access_keys.txt') as json_file:
    keys = json.load(json_file)

#api entry points/keys
#test instance API_KEY
API_KEY = keys['beta']
API_URL = "https://cms.beta.instructure.com"
#instantiate Canvas object
canvas = Canvas(API_URL, API_KEY)

#helper functions

#Find section based on section name. Returns -1 if not found

def section_id_search(course_id, section_name):
    '''
    Returns section ID for given course section. Returns -1 if not found
    '''
    list_sections = canvas.get_course(course_id).get_sections()
    target_section = None
    for section in list_sections:
        if(section.name.lower() == section_name.lower()):
            target_section = section
            break
    
    return target_section.id if target_section != None else -1

#Create dictionary of section names and return dict.

def section_dict(course_id):
    sections = canvas.get_course(course_id).get_sections()
    section_dict={}
    for s in sections:
        section_dict[s.name.split(' ')[0]] = s.id
    return section_dict

#function -- enroll student object into given course

def enroll_student(studentObj, courseID):
    x = section_dict(courseID)
    enrollment_id = -1
    if studentObj['Grade_Level'] + 'th' in x:
            section_id = x[studentObj['Grade_Level'] + 'th']
            try:
                student_id = canvas.get_user('student_' + studentObj['DCID'], 'sis_user_id')
            except:
                tqdm.write("Student not in Canvas, skipping")
                return
            enrollment_id=course.get_section(section_id).enroll_user(student_id.id, 
            enrollment= {
            'type': 'StudentEnrollment',
            'enrollment_state': 'active',
            'notify': 'false'
            
            })
            tqdm.write("Student " + studentObj['First_Name'] +" " + studentObj['Last_Name'] + " enrolled with Enrollment ID: " + str(enrollment_id.id))
    else:
        tqdm.write("Student " + studentObj['First_Name'] +" " + studentObj['Last_Name'] + " enrolled already")

#retrive DCID from sis_user_id object (get rid of student_)
def sis_id(obj):
    return obj.sis_user_id.split("_")[1]

#deactivate enrollment
def de_enroll(enroll_obj):
    enroll_obj.deactivate(task="conclude")
    tqdm.write("De-enrolled student: " + enroll_obj.user['name'])

def append_to_list_faster(obj, list):
    list.append(obj)

#CSV read
student_list = []
print(os.path.dirname(os.getcwd()))
with open(os.path.dirname(os.getcwd()) + '/roster.csv') as csvfile:
    reader= csv.DictReader(csvfile)
    for row in reader:
        student_list.append(row)

#get DCIDs of people enrolled in Powerschool
ps_dcid = [student['DCID'] for student in student_list]

#get DCIDs of people enrolled in Canvas course
course= canvas.get_course(276682)
enrollments = course.get_enrollments(type=['StudentEnrollment'])
pag_list_users = [users for users in tqdm(enrollments, desc="getting enrollments....", unit="users")]
print("getting current enrolled DCIDs")
enrolled_dcid = thread_map(sis_id, pag_list_users, max_workers=10, unit="students", desc="getting dcids..." )
#gets student_<dcid>
#print(pag_list_users[0].sis_user_id)

#let's diff the lists.
#first, find who to enroll. these student are in ps_dcid but not in enrolled_dcid
to_enroll = [dcid for dcid in ps_dcid if dcid not in enrolled_dcid]
to_enroll_obj = [obj for obj in student_list if obj['DCID'] in to_enroll]
#next, to de-enroll. these students are in enrolled_dcid but not in ps_dcid
to_deenroll = [dcid for dcid in enrolled_dcid if dcid not in ps_dcid]
#gonna need those enrollment objects for these dcids
to_deenroll_obj = [obj for obj in pag_list_users if sis_id(obj) in to_deenroll]

#print(to_enroll_obj)
# print(to_deenroll)
# print(to_deenroll_obj)

#now enroll
hough_enroll = partial(enroll_student, courseID=276682)
results = thread_map(hough_enroll, to_enroll_obj, max_workers=5, unit="students", desc="enrolling users...")

#de-enroll
results = thread_map(de_enroll, to_deenroll_obj, max_workers=5, unit="students", desc="de-enrolling users...")
