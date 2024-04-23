from typing import Tuple

class Classroom:
    def __init__(self, name: str, capacity: int, subjects: list):
        self.name = name
        self.capacity = capacity
        self.subjects = subjects
        # Keep the courses that are held in a class for each time slot so that later
        # conflicts could be spotted (2 or more coreses in the same class at the same time).
        self.courses_by_time_slot = {}  # Dict [time_slot: List[course]]
    
    def get_name(self) -> str:
        return self.name

    def get_capacity(self) -> int:
        return self.capacity
    
    def can_host_course(self, course: str) -> bool:
        return course in self.subjects
    
    def is_occupied_at_time(self, time_slot: str) -> bool:
        return time_slot in self.courses_by_time_slot
    
    def add_course(self, course: str, time_slot: Tuple[str, Tuple[int, int]]):
        if time_slot not in self.courses_by_time_slot:
            self.courses_by_time_slot[time_slot] = []
        self.courses_by_time_slot[time_slot].append(course)

    def remove_course(self, course: str, time_slot: Tuple[str, Tuple[int, int]]):
        if (time_slot in self.courses_by_time_slot 
            and course in self.courses_by_time_slot[time_slot]):
            self.courses_by_time_slot[time_slot].remove(course)
            if len(self.courses_by_time_slot[time_slot]) == 0:
                del self.courses_by_time_slot[time_slot]

    # Caulculates the number of hard conflicts caused by two or more 
    # courses being scheduled in the same classroom at the same time.
    def count_overlaps(self) -> int:
        hard_conflicts = 0

        for time_slot in self.courses_by_time_slot:
            if len(self.courses_by_time_slot[time_slot]) > 1:
                hard_conflicts += 1
        return hard_conflicts