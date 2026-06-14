from setuptools import find_packages, setup


setup(
    name="werewolf-langgraph",
    version="0.1.0",
    description="LangGraph multi-agent Werewolf game",
    python_requires=">=3.9",
    package_dir={"": "src"},
    packages=find_packages("src"),
    package_data={
        "werewolf_langgraph": [
            "static/*.html",
            "static/*.css",
            "static/*.js",
            "static/assets/*.webp",
            "static/assets/avatars/*.webp",
        ]
    },
    install_requires=[
        "langgraph>=0.2.0",
        "langchain-core>=0.3.0",
        "langchain-openai>=0.2.0",
        "python-dotenv>=1.0.1",
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.30.0",
    ],
    entry_points={
        "console_scripts": [
            "werewolf-check-deepseek=werewolf_langgraph.check_deepseek:main",
            "werewolf-web=werewolf_langgraph.web:main",
        ]
    },
)
