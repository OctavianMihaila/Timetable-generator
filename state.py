import random
import copy
from typing import Dict
from schedule import Schedule

class State:
    def __init__(self, schedule: Schedule,
                hard_conflicts: int = 0, 
                soft_conflicts: int = 0):
        
        self.schedule = schedule
        self.hard_conflicts = hard_conflicts
        self.soft_conflicts = soft_conflicts
        self.nr_seats_per_course = {}  # Dict [course_name: nr_seats]

    def is_final(self) -> bool:
        return self.hard_conflicts == 0 and self.soft_conflicts == 0
    
    def get_all_conflicts(self) -> int:
        return self.hard_conflicts + self.soft_conflicts

    def get_hard_conflicts(self) -> int:
        return self.hard_conflicts
    
    def get_soft_conflicts(self) -> int:
        return self.soft_conflicts
    
    def get_schedule(self) -> Schedule:
        return self.schedule
    
    def get_nr_seats_per_course(self) -> Dict[str, int]:
        return self.nr_seats_per_course
    
    def increase_nr_seats_per_course(self, course_name: str, nr_seats: int):
        if course_name in self.nr_seats_per_course:
            self.nr_seats_per_course[course_name] += nr_seats
        else:
            self.nr_seats_per_course[course_name] = nr_seats

    # Checks if all the students are covered by the current schedule
    # Returns the number of hard conflicts caused by not enough seats
    def conflicts_caused_by_not_enough_seats(self):
        hard_conflicts = 0

        for course in self.schedule.courses:
            if course not in self.nr_seats_per_course:
                hard_conflicts += 1
            elif self.nr_seats_per_course[course] < self.schedule.courses[course]:
                hard_conflicts += 1

        return hard_conflicts
    
    def compute_hard_conflicts(self) -> int:
        hard_conflicts = 0
        assignments = self.schedule.get_assignments()

        for course_name, assignment_list in assignments.items():
            for assignment in assignment_list:
                classroom = self.schedule.classrooms[assignment[0]]
                teacher = self.schedule.teachers[assignment[1]]
                time_slot = assignment[2]

                if not teacher.can_teach_course(course_name):
                    hard_conflicts += 1

                if not classroom.can_host_course(course_name):
                    hard_conflicts += 1

                # Count the number of seats allocated for each course
                if course_name not in self.nr_seats_per_course:
                    self.nr_seats_per_course[course_name] = 0

                self.nr_seats_per_course[course_name] += classroom.get_capacity()

        # Check if all students are assigned to a classroom
        hard_conflicts += self.conflicts_caused_by_not_enough_seats()
        # Count the hard conflicts caused by teachers
        for teacher_name, teacher in self.schedule.teachers.items():
            # Check if the teacher is teaching too much
            if len(teacher.get_courses_by_time_slot()) > 7:
                hard_conflicts += 1

            overlaps = teacher.count_overlaps()
            if  overlaps > 0:
                hard_conflicts += overlaps

        # Count the hard conflicts caused by classrooms
        for classroom_name, classroom in self.schedule.classrooms.items():
            overlaps = classroom.count_overlaps()
            if overlaps > 0:
                hard_conflicts += overlaps

        self.hard_conflicts = hard_conflicts

    def compute_soft_conflicts(self) -> int:
        soft_conflicts = 0
        
        # Check weather a teacher has a course at a time that is not in his preffered time slots
        for teacher in self.schedule.teachers:
            teacher = self.schedule.teachers[teacher]
            for time_slot in teacher.get_courses_by_time_slot():
                if time_slot not in teacher.get_preffered_time_slots():
                    soft_conflicts += 1

        self.soft_conflicts = soft_conflicts

    def generate_initial_schedule(self):
        assignments = {}

        for course, num_students in self.schedule.courses.items():
            remaining_students = num_students

            # Randomly choose a classroom and a teacher for each course
            available_classrooms = list(self.schedule.classrooms.keys())
            available_teachers = list(self.schedule.teachers.keys())
            random.shuffle(available_classrooms)
            random.shuffle(available_teachers)

            while remaining_students > 0:
                assigned = False

                for classroom in available_classrooms:
                    # Look for a free time slot in the classroom
                    time_slot = self.schedule.find_free_time_slot(classroom,
                                                                self.schedule.get_available_time_slots())
                    if time_slot is None: # No time slot available
                        continue
                    classroom_as_class = self.schedule.get_classrooms()[classroom]

                    if (classroom_as_class.can_host_course(course) and
                            not classroom_as_class.is_occupied_at_time(time_slot)):

                        for teacher in available_teachers:
                            teacher_as_class = self.schedule.get_teachers()[teacher]

                            if (not teacher_as_class.is_teaching_too_much() and
                                teacher_as_class.is_free_at_time(time_slot) and
                                teacher_as_class.has_available_time_slot() and
                                teacher_as_class.can_teach_course(course)):

                                # Assign the course to the classroom and teacher
                                if course and classroom and teacher and time_slot:
                                    assignments.setdefault(course, []).append((classroom,
                                                                                teacher, time_slot))
                                    classroom_as_class.add_course(course, time_slot)
                                    teacher_as_class.add_course(course, time_slot)
                                    remaining_students -= self.schedule.classrooms[classroom].get_capacity()
                                    assigned = True
                                    break
                        
                    if remaining_students <= 0:
                        break

                # Can't find a combination so that a new course is assigned.
                if not assigned:
                    break

        self.schedule.set_assignments(assignments)
        self.compute_hard_conflicts()
        self.compute_soft_conflicts()

    def apply_move(self, move: str):
        neighbor_state = copy.deepcopy(self)

        if move == "switch_teachers_soft_conflict":
            neighbor_state.switch_teachers_soft_conflict()
            neighbor_state.switch_teachers_soft_conflict()
            neighbor_state.switch_teachers_soft_conflict()
        elif move == "move_course_to_free_slot":
            neighbor_state.get_schedule().move_course_to_free_slot()
            neighbor_state.get_schedule().move_course_to_free_slot()
            neighbor_state.get_schedule().move_course_to_free_slot()
        elif move == "switch_courses_same_classroom":
            neighbor_state.get_schedule().switch_courses_same_classroom()
            neighbor_state.get_schedule().switch_courses_same_classroom()
            neighbor_state.get_schedule().switch_courses_same_classroom()
        elif move == "move_course_to_free_slot_no_conflicts":
            neighbor_state.get_schedule().move_course_to_free_slot_no_conflicts()
            neighbor_state.get_schedule().move_course_to_free_slot_no_conflicts()
            neighbor_state.get_schedule().move_course_to_free_slot_no_conflicts()
        else:
            print("Invalid move.")
            return

        neighbor_state.compute_hard_conflicts()
        neighbor_state.compute_soft_conflicts()

        return neighbor_state

    # Looks for two teachers that can teach each other's course
    # and that have courses that cause soft conflicts
    def switch_teachers_soft_conflict(self):
        max_attempts = 1000
        attempts = 0

        while attempts < max_attempts:
            # Pick two random teachers that have coruses that cause soft conflicts
            teacher_candidates = [teacher for teacher in self.schedule.teachers.values() if
                                    teacher.get_courses_that_cause_soft_conflicts()]
            teacher1 = random.choice(teacher_candidates) if teacher_candidates else None

            other_teacher_candidates = [teacher for teacher in self.schedule.teachers.values() if
                                            teacher.get_courses_that_cause_soft_conflicts() and
                                            teacher != teacher1] if teacher1 else []
            teacher2 = random.choice(other_teacher_candidates) if other_teacher_candidates else None

            if not teacher1 or not teacher2:
                # print("No teachers found that cause soft conflicts.") # TODO: Log this
                return
            
            # Get the courses that cause soft conflicts for teacher1 and teacher2
            teacher1_soft_conflicts = teacher1.get_courses_that_cause_soft_conflicts()
            teacher2_soft_conflicts = teacher2.get_courses_that_cause_soft_conflicts()

            # Find a course that teacher1 has and teacher2 can teach. # returns (time slot, course)
            course_t2_can_teach_from_t1 = teacher2.find_course_in_other_teacher_conflicts(teacher1_soft_conflicts) 
            # Find a course that teacher2 has and teacher1 can teach. # returns (time slot, course)
            course_t1_can_teach_from_t2 = teacher1.find_course_in_other_teacher_conflicts(teacher2_soft_conflicts) 

            if course_t2_can_teach_from_t1 and course_t1_can_teach_from_t2:
                time_slot_1 = course_t2_can_teach_from_t1[0]
                time_slot_2 = course_t1_can_teach_from_t2[0]

                if not teacher1.is_free_at_time(time_slot_2) or not teacher2.is_free_at_time(time_slot_1):
                    attempts += 1
                    continue

                # Switch the teachers for the courses by updating the assignments and teachers courses_by_time_slot
                teacher1.remove_course(course_t2_can_teach_from_t1[1], time_slot_1)
                teacher2.remove_course(course_t1_can_teach_from_t2[1], time_slot_2)
                teacher1.add_course(course_t2_can_teach_from_t1[1], time_slot_1)
                teacher2.add_course(course_t1_can_teach_from_t2[1], time_slot_2)

                # Update the assignments
                self.schedule.switch_teachers_in_assignments(teacher1, teacher2, course_t2_can_teach_from_t1,
                                                                course_t1_can_teach_from_t2)
                return

            attempts += 1

    def get_next_states(self):
        next_states = []
        
        # Generate all possible moves
        moves = ["switch_teachers_soft_conflict", "move_course_to_free_slot",
                    "switch_courses_same_classroom", "move_course_to_free_slot_no_conflicts"]

        for move in moves:
            next_states.append(self.apply_move(move))

        return next_states