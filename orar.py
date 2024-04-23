import sys
import utils
import time
import random
import copy
from typing import Tuple
from teacher import Teacher
from classroom import Classroom
from schedule import Schedule
from state import State

def stochastic_hill_climbing(initial: State, max_iters: int = 10000,
                              max_no_improvement: int = 100) -> Tuple[bool, int, int, State]:
    iters, states, no_improvement = 0, 0, 0
    state = copy.deepcopy(initial)

    while iters < max_iters and no_improvement < max_no_improvement:
        iters += 1

        # Get all possible neighbors
        neighbors = state.get_next_states()

        # Choose from the neighbors that are better than the current state
        better_neighbors = [neighbor for neighbor in neighbors 
                            if neighbor.get_hard_conflicts() <= state.get_hard_conflicts() and
                            neighbor.get_soft_conflicts() <= state.get_soft_conflicts()]

        if not better_neighbors:
            break  # Local minimum reached, no better neighbors

        # Alegem aleator între vecinii mai buni
        new_state = random.choice(better_neighbors)
        states += len(neighbors)

        if (new_state.get_hard_conflicts() >= state.get_hard_conflicts() and
            new_state.get_soft_conflicts() >= state.get_soft_conflicts()):
            no_improvement += 1
        else:
            no_improvement = 0

        state = new_state

    return state.is_final(), iters, states, state

# Wrapper function so that we can init variables and call the recursive function
class CSP:
    def __init__(self, initial_state: State):
        self.current_state = initial_state

    # domains: [course: [(classroom, teacher, time_slot)]
    def generate_domains(self):
        domains = {}
        schedule = self.current_state.get_schedule()

        for course in schedule.courses.keys():
            domains[course] = []
            for classroom_name in schedule.classrooms.keys():
                for teacher_name in schedule.teachers.keys():
                    for time_slot in schedule.available_time_slots:
                        # Check if the assignment satisfies constraints
                        if self.check_domain_constraints(course, classroom_name,
                                                        teacher_name, time_slot):
                            domains[course].append((classroom_name, teacher_name, time_slot))
        return domains
    
    # Used to filter the domains of the variables, so that we choose only from valid assignments
    def check_domain_constraints(self, course, classroom, teacher, time_slot):
        schedule = self.current_state.get_schedule()

        if (not time_slot in schedule.teachers[teacher].get_preffered_time_slots() or
            schedule.classrooms[classroom].is_occupied_at_time(time_slot) or
            not schedule.classrooms[classroom].can_host_course(course) or
            not schedule.teachers[teacher].can_teach_course(course)):
            return False
        
        return True
    
    def generate_constraints(self):
        constraints = []
        schedule = self.current_state.get_schedule()

        def is_classroom_occupied(params):
            _, classroom, _, time_slot = params
            return not schedule.classrooms[classroom].is_occupied_at_time(time_slot)


        def is_course_suitable_for_classroom(params):
            course, classroom, _, _ = params
            return schedule.classrooms[classroom].can_host_course(course)

        def is_teacher_suitable(params):
            course, _, teacher, _ = params
            return schedule.teachers[teacher].can_teach_course(course)

        def is_preferred_time_slot(params):
            _, _, teacher, time_slot = params
            return time_slot in schedule.teachers[teacher].get_preffered_time_slots()

        def is_teacher_available(params):
            _, _, teacher, time_slot = params
            return schedule.teachers[teacher].is_free_at_time(time_slot)

        def is_teacher_any_time_available(params):
            _, _, teacher, _ = params
            return schedule.teachers[teacher].has_available_time_slot()

        def is_teacher_teaching_too_much(params):
            _, _, teacher, _ = params
            return len(schedule.teachers[teacher].get_courses_by_time_slot()) < 7

        def has_classroom_overlapping_courses(params):
            _, classroom, _, _ = params
            return schedule.classrooms[classroom].count_overlaps() == 0

        def has_teacher_overlapping_courses(params):
            _, _, teacher, _ = params
            return schedule.teachers[teacher].count_overlaps() == 0

        # Append all constraint templates to the constraints list
        constraints.append(is_classroom_occupied)
        constraints.append(is_course_suitable_for_classroom)
        constraints.append(is_teacher_suitable)
        constraints.append(is_preferred_time_slot)
        constraints.append(is_teacher_available)
        constraints.append(is_teacher_any_time_available)
        constraints.append(is_teacher_teaching_too_much)
        constraints.append(has_classroom_overlapping_courses)
        constraints.append(has_teacher_overlapping_courses)

        return constraints
    
    def check_constraint(self, constraint, assignments, params):
        if not constraint(params):
            return False
        
        return True
    
    def solve(self):
        domains = self.generate_domains()
        constraints = self.generate_constraints()

        # We want to start with the course that has the least number of teachers
        # Because it is more constrained and it is more likely to have a unique solution,
        self.current_state.get_schedule().reorder_by_nr_teachers()

        def backtrack():
            schedule = self.current_state.get_schedule()
            assignments = schedule.get_assignments()

            # Checking if all students are covered
            if self.current_state.conflicts_caused_by_not_enough_seats() == 0:
                return self.current_state

            course = None
            
            # pick a course that has not yer covered all the students.
            for course_name, num_students in schedule.courses.items():
                if (course_name not in assignments or
                    self.current_state.get_nr_seats_per_course()[course_name] < num_students):
                    course = course_name
                    break

            if course == None:
                return self.current_state

            for value in domains[course]:
                classroom_name = value[0]
                teacher_name = value[1]
                time_slot = value[2]

                teacher = schedule.get_teachers()[teacher_name]
                classroom = schedule.get_classrooms()[classroom_name]
                assignments.setdefault(course, []).append(value)

                params = (course, classroom_name, teacher_name, time_slot)
                constraints_satisfied = True

                for constraint in constraints:
                    if not self.check_constraint(constraint, assignments, params): # Constraint is not satisfied
                        assignments[course].remove(value)
                        constraints_satisfied = False
                        break

                if not constraints_satisfied:
                    continue
                        
                # Assign the course to a teacher and classroom
                teacher.add_course(course, time_slot)
                classroom.add_course(course, time_slot)
                self.current_state.increase_nr_seats_per_course(course, classroom.get_capacity())

                result = backtrack()
                if result:
                    return result
                
                # Remove the course from the assignment in case the result is None
                assignments[course].remove(value)
                teacher.remove_course(course, time_slot)
                classroom.remove_course(course, time_slot)

            return None
        
        # Start backtracking with an empty assignment
        return backtrack()

if __name__ == '__main__':
    start_time = time.time()


    used_algorithm = sys.argv[1]
    filename = sys.argv[2]
    in_data = utils.read_yaml_file(filename)

    schedule = Schedule(in_data)
    initial_state = State(schedule)

    if used_algorithm == 'hc':
        initial_state.generate_initial_schedule()

        print("Hard conflicts in initial state: " + str(initial_state.get_hard_conflicts()))
        print("Soft conflicts in initial state: " + str(initial_state.get_soft_conflicts()))
        print('Initial state schedule:')
        print(utils.pretty_print_timetable(initial_state.get_schedule().convert_schedule_to_dict(), filename))

        final_state = stochastic_hill_climbing(initial_state)
        print("Number of generated states: " + str(final_state[2]))
        print("Final state hard conflicts: " + str(final_state[3].get_hard_conflicts()))
        print("Final state soft conflicts: " + str(final_state[3].get_soft_conflicts()))
        print('Final state schedule:')
        print(utils.pretty_print_timetable(final_state[3].get_schedule().convert_schedule_to_dict(), filename))

        with open(f'outputs/{filename[7:-5]}.txt', 'w') as f:
            f.write(utils.pretty_print_timetable(final_state[3].get_schedule().convert_schedule_to_dict(), filename))

    elif used_algorithm == 'csp':
        csp = CSP(initial_state)

        final_state = csp.solve()
        print(utils.pretty_print_timetable(final_state.get_schedule().convert_schedule_to_dict(), filename))
        print("Final state hard conflicts: " + str(final_state.get_hard_conflicts()))
        print("Final state soft conflicts: " + str(final_state.get_soft_conflicts()))
        with open(f'outputs/{filename[7:-5]}.txt', 'w') as f:
            f.write(utils.pretty_print_timetable(final_state.get_schedule().convert_schedule_to_dict(), filename))

    print("--- %s seconds ---" % (time.time() - start_time))
    