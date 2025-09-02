from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class Rubric():
    """Educational Assessment Rubric Generation Crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    
    @agent
    def question_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['question_analyzer'], # type: ignore[index]
            verbose=True
        )

    @agent
    def diagram_interpreter(self) -> Agent:
        return Agent(
            config=self.agents_config['diagram_interpreter'], # type: ignore[index]
            verbose=True
        )

    @agent
    def rubric_designer(self) -> Agent:
        return Agent(
            config=self.agents_config['rubric_designer'], # type: ignore[index]
            verbose=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    
    @task
    def question_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['question_analysis_task'], # type: ignore[index]
        )

    @task
    def diagram_interpretation_task(self) -> Task:
        return Task(
            config=self.tasks_config['diagram_interpretation_task'], # type: ignore[index]
            context=[self.question_analysis_task()]  # Depends on question analysis
        )

    @task
    def rubric_generation_task(self) -> Task:
        return Task(
            config=self.tasks_config['rubric_generation_task'], # type: ignore[index]
            context=[self.question_analysis_task(), self.diagram_interpretation_task()],  # Depends on both previous tasks
            output_file='rubrics.json'
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Educational Assessment Rubric Generation crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )