import random
from typing import List, Tuple, Dict
from classroom import Classroom
from teacher import Teacher

class Schedule:
    def __init__(self, in_data):
        intervals = in_data['Intervale'] # List of tuples
        courses = in_data['Materii'] # Dict [course_name: nr_students]
        days = in_data['Zile'] # List of strings
        available_time_slots = generate_available_time_slots(intervals, days)

        classrooms = in_data['Sali']
        for classroom in classrooms:
            classrooms[classroom] = Classroom(classroom, classrooms[classroom]['Capacitate'],
                                                classrooms[classroom]['Materii'])

        teachers = in_data['Profesori']
        for teacher in teachers:
            constraints = teachers[teacher]['Constrangeri']
            preffered_time_slots = self.find_preffered_time_slots(teachers[teacher]['Constrangeri'],
                                                                    days, intervals)
            teachers[teacher] = Teacher(teacher, constraints,
                                            teachers[teacher]['Materii'], preffered_time_slots)

        self.intervals = intervals
        self.days = days
        self.courses = courses
        self.classrooms = classrooms
        self.teachers = teachers
        self.available_time_slots = available_time_slots
        self.assignments = {}  # Course name to list of (classroom, teacher, time slot)

    def get_assignments(self):
        return self.assignments
    
    def get_classrooms(self):
        return self.classrooms
    
    def get_teachers(self):
        return self.teachers
    
    def set_assignments(self, assignments):
        self.assignments = assignments

    def get_available_time_slots(self):
        return self.available_time_slots

    # Checks whether a course can be held in a specific classroom
    def can_class_host_course(self, course: str, classroom: str) -> bool:
        return (course in self.courses and classroom in self.classrooms and
            course in self.classrooms[classroom].subjects)
    
    def find_free_time_slot(self, classroom: str, target_time_slots: List[Tuple[str, Tuple[int, int]]],
                                max_attempts: int = 100) -> Tuple[str, Tuple[int, int]]:
        attempts = 0

        while attempts < max_attempts:
            time_slot = random.choice(target_time_slots)

            if not self.classrooms[classroom].is_occupied_at_time(time_slot):
                return time_slot
            attempts += 1
        
        return None
    
    # Checks if interval1 is included in interval2
    def included_in_interval(self, interval1, interval2):
        # convert the intervals to a tuple
        if type(interval1) == str:
            interval1 = eval(interval1)

        if type(interval2) == str:
            interval2 = eval(interval2)

        return interval1[0] >= interval2[0] and interval1[1] <= interval2[1]
    
    def find_preffered_time_slots(self, constraints: List[str], days: List[str],
                                    intervals: List[str]) -> List[Tuple[str, Tuple[int, int]]]:
        available_time_slots = []

        for constraint in constraints:
            if constraint.startswith('!'):
                if '-' in constraint:
                    banned_interval = convert_interval_format(constraint[1:])
                    intervals = [interval for interval in intervals if
                                    not self.included_in_interval(interval, banned_interval)]
                else:
                    days = [day for day in days if day != constraint[1:]]
        
        for day in days:
            for interval in intervals:
                available_time_slots.append((day, interval))

        return available_time_slots
    
    # Reorder the courses by the number of teachers that can teach them
    def reorder_by_nr_teachers(self):
        nr_teachers_per_course = {}
        for course in self.courses:
            nr_teachers_per_course[course] = 0

        for teacher in self.teachers:
            for course in self.teachers[teacher].courses:
                nr_teachers_per_course[course] += 1

        self.courses = dict(sorted(self.courses.items(),
                                    key=lambda item: nr_teachers_per_course[item[0]], reverse=False))

    # Converts assignments to a dictionary that can be pretty printed by the utils module
    def convert_schedule_to_dict(self) -> Dict[str, Dict[Tuple[int, int], Dict[str, Tuple[str, str]]]]:
        # Dict of days to dict of intervals to dict of classrooms to tuple of teacher and course
        pretty_print_schedule = {}

        for day in self.days:
            pretty_print_schedule[day] = {}
            for interval in self.intervals:
                pretty_print_schedule[day][eval(interval)] = {}
                for classroom in self.classrooms:
                    classroom_name = self.classrooms[classroom].get_name()
                    pretty_print_schedule[day][eval(interval)][classroom_name] = None

        for course, assignments in self.assignments.items():
            for assignment in assignments:
                classroom, teacher, time_slot = assignment
                day, interval = time_slot
                teacher_name = self.teachers[teacher].get_name()
                classroom_name = self.classrooms[classroom].get_name()
                pretty_print_schedule[day][eval(interval)][classroom_name] = (teacher_name, course)


        return pretty_print_schedule
    
    # Switeches the teachers in the assignments of two courses
    def switch_teachers_in_assignments(self, teacher1, teacher2,
                                        course_t2_can_teach_from_t1, course_t1_can_teach_from_t2):
        course_t2_can_teach_from_t1_assignments = self.assignments[course_t2_can_teach_from_t1[1]]
        course_t1_can_teach_from_t2_assignments = self.assignments[course_t1_can_teach_from_t2[1]]

        for assignment in course_t2_can_teach_from_t1_assignments:
            if assignment[2] == course_t2_can_teach_from_t1[0] and assignment[1] == teacher1.get_name():
                classroom = assignment[0]
                course_t2_can_teach_from_t1_assignments.remove(assignment)
                course_t1_can_teach_from_t2_assignments.append((classroom, teacher2.get_name(),
                                                                    course_t2_can_teach_from_t1[0]))
                break

        for assignment in course_t1_can_teach_from_t2_assignments:
            if assignment[2] == course_t1_can_teach_from_t2[0] and assignment[1] == teacher2.get_name():
                classroom = assignment[0]
                course_t1_can_teach_from_t2_assignments.remove(assignment)
                course_t2_can_teach_from_t1_assignments.append((classroom, teacher1.get_name(),
                                                                    course_t1_can_teach_from_t2[0]))
                break

    # Find a teacher that has a course that cause conflicts and move it
    # to a free time slot if that solves the conflict.
    def move_course_to_free_slot(self):
        for course_name, assignment in self.assignments.items():
            for course in assignment:
                classroom, teacher, time_slot = course
                teacher = self.teachers[teacher]
                classroom = self.classrooms[classroom]

                preffered_time_slots = teacher.get_preffered_time_slots()
                # Find a free time slot in which the teacher is willing to teach the course.
                free_time_slot = self.find_free_time_slot(classroom.get_name(), preffered_time_slots)
                soft_conflicts = teacher.get_courses_that_cause_soft_conflicts()

                if soft_conflicts and free_time_slot and teacher.is_free_at_time(free_time_slot):
                    # Move the course to the free time slot
                    teacher.remove_course(course_name, time_slot)
                    teacher.add_course(course_name, free_time_slot)
                    classroom.remove_course(course_name, time_slot)
                    classroom.add_course(course_name, free_time_slot)
                    
                    # Update the assignments
                    self.assignments[course_name].remove((classroom.get_name(),
                                                            teacher.get_name(), time_slot))
                    self.assignments[course_name].append((classroom.get_name(),
                                                            teacher.get_name(), free_time_slot))
                    return
    
    # Look for a course that is currenlty held in received classroom and the teacher
    # is fine with the future time slot of the course.
    def find_course_that_moved_causes_no_conflicts(self, classroom, future_time_slot):
        for course_name, assignment in self.assignments.items():
            for course in assignment:
                teacher = self.teachers[course[1]]
                current_classroom = self.classrooms[course[0]]
                time_slot = course[2]

                if current_classroom == classroom and classroom.can_host_course(course_name):
                    if future_time_slot in teacher.get_preffered_time_slots():
                        return course_name, teacher, time_slot
        
        return None

    # Find courses that are held in the same classroom at different times.
    # If the switch solves at least one conflict, withouth creating new ones,
    # then switch the time slots of the courses.
    def switch_courses_same_classroom(self):
        for course_name, assignment in self.assignments.items():
            for course in assignment:
                classroom, teacher, time_slot = course
                teacher = self.teachers[teacher]
                classroom = self.classrooms[classroom]
                teacher_soft_conflicts = teacher.get_courses_that_cause_soft_conflicts()
                
                if not teacher_soft_conflicts:
                    continue

                res = self.find_course_that_moved_causes_no_conflicts(classroom, time_slot)

                if res != None:
                    new_course_name, new_teacher, new_time_slot = res

                    # Switch the time slots of the courses
                    teacher.remove_course(course_name, time_slot)
                    teacher.add_course(course_name, new_time_slot)
                    classroom.remove_course(course_name, time_slot)
                    classroom.add_course(course_name, new_time_slot)

                    new_teacher.remove_course(new_course_name, new_time_slot)
                    new_teacher.add_course(new_course_name, time_slot)
                    classroom.remove_course(new_course_name, new_time_slot)
                    classroom.add_course(new_course_name, time_slot)

                    # Update the assignments
                    self.assignments[course_name].remove((classroom.get_name(),
                                                            teacher.get_name(), time_slot))
                    self.assignments[course_name].append((classroom.get_name(),
                                                            teacher.get_name(), new_time_slot))
                    self.assignments[new_course_name].remove((classroom.get_name(),
                                                                new_teacher.get_name(), new_time_slot))
                    self.assignments[new_course_name].append((classroom.get_name(),
                                                                new_teacher.get_name(), time_slot))

                    return

    # Move a course to a free time slot if this action cause no conflicts
    def move_course_to_free_slot_no_conflicts(self):
        max_iter = 100
        count_iter = 0

        while count_iter < max_iter:
            # Pick a random assignment
            course_name, assignment = random.choice([(course_name, assignment) for course_name,
                                                        assignment in self.assignments.items()])
            assignment = assignment[0]
            classroom_name = assignment[0]
            teacher_name = assignment[1]
            old_time_slot = assignment[2]

            # Find a free time slot that do not cause conflicts
            time_slot = self.find_free_time_slot(assignment[0], self.available_time_slots)

            if time_slot:
                # remove the course from the current time slot
                self.assignments[course_name].remove(assignment)
                self.classrooms[classroom_name].remove_course(course_name, old_time_slot)
                self.teachers[teacher_name].remove_course(course_name, old_time_slot)

                # add the course to the new time slot
                self.assignments[course_name].append((classroom_name, teacher_name, time_slot))
                self.classrooms[classroom_name].add_course(course_name, time_slot)
                self.teachers[teacher_name].add_course(course_name, time_slot)

                return

            count_iter += 1
    
def generate_available_time_slots( intervals: List[Tuple[int, int]], days: List[str]
                                    ) -> List[Tuple[str, Tuple[int, int]]]:

    time_slots = [] # List of pairs (day, interval)

    for day in days:
        for interval in intervals:
            time_slots.append((day, interval))
    return time_slots

# Convert interval in format h1-h2 to a string like (h1, h2)
def convert_interval_format(interval: str) -> str:
    interval = "(" + interval.replace('-', ', ') + ")"
    return interval