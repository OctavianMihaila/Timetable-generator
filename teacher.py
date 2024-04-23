from typing import List, Dict, Tuple

class Teacher:
    def __init__(self, name: str, constraints: List[str], courses: List[str],
                    preffered_time_slots: Dict[str, List[str]]):
        self.name = name
        self.courses = courses  # List of courses they can teach
        self.constraints = constraints  # List of constraints
        self.preffered_time_slots = preffered_time_slots # List of preffered time slots
        self.courses_by_time_slot = {}  # Dict [time_slot: List[course]]

    def get_name(self) -> str:
        return self.name
    
    def get_courses_by_time_slot(self) -> Dict[Tuple[str, Tuple[int, int]], List[str]]:
        return self.courses_by_time_slot
    
    def get_constraints(self) -> List[str]:
        return self.constraints
    
    def get_preffered_time_slots(self) -> Dict[str, List[str]]:
        return self.preffered_time_slots
    
    # Returns the courses that cuase soft conflicts for a teacher
    def get_courses_that_cause_soft_conflicts(self) -> Dict[Tuple[str, Tuple[int, int]], List[str]]:
        conflicting_courses = {}
        for slot in self.courses_by_time_slot:
            if slot not in self.preffered_time_slots:
                conflicting_courses[slot] = self.courses_by_time_slot[slot]

        return conflicting_courses

    def can_teach_course(self, course: str) -> bool:
        return course in self.courses
    
    # A teacher can be assigned to max number of preffered time slots.
    def has_available_time_slot(self) -> bool:
        nr_courses_by_time_slot = 0
        for slot in self.courses_by_time_slot:
            nr_courses_by_time_slot += len(self.courses_by_time_slot[slot])

        return nr_courses_by_time_slot < len(self.preffered_time_slots)

    def is_teaching_too_much(self) -> bool:
        # check if the teacher has more than 7 assignments per week
        if len(self.courses_by_time_slot) >= 7:
            return True
        
        return False
    
    def is_free_at_time(self, time_slot: Tuple[str, Tuple[int, int]]) -> bool:
        return time_slot not in self.courses_by_time_slot
    
    def add_course(self, course: str, time_slot: Tuple[str, Tuple[int, int]]):
        if time_slot not in self.courses_by_time_slot:
            self.courses_by_time_slot[time_slot] = []
        self.courses_by_time_slot[time_slot].append(course)

    def remove_course(self, course: str, time_slot: Tuple[str, Tuple[int, int]]):
        if time_slot in self.courses_by_time_slot and course in self.courses_by_time_slot[time_slot]:
            self.courses_by_time_slot[time_slot].remove(course)
            if len(self.courses_by_time_slot[time_slot]) == 0:
                del self.courses_by_time_slot[time_slot]

    def find_course_in_other_teacher_conflicts(self, other_teacher_soft_conflicts):
        result = None # (time slot, course)

        for time_slot, courses in other_teacher_soft_conflicts.items():
            for course in courses:
                # Check if teacher2 can teach course1
                if self.can_teach_course(course) and time_slot not in self.preffered_time_slots:
                    result = (time_slot, course)

        return result
    
    # Count the number of courses that a teacher is teaching at the same time
    def count_overlaps(self) -> bool:
        nr_conflicts = 0

        for slot in self.courses_by_time_slot:
            courses = self.courses_by_time_slot[slot]
            if len(courses) > 1:
                nr_conflicts += len(courses) - 1

        return nr_conflicts
