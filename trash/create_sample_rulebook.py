#!/usr/bin/env python3
"""
Script to create a sample rulebook with the proper schema
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from maestro.main import get_rulebook_file_path, load_rulebook, save_rulebook, Rulebook, Rule, RuleMatch, MatchCondition, RuleAction, RuleVerify

def create_sample_rulebook():
    # Create the U++ Vector/Moveable rule
    rule = Rule(
        id="upp_vector_moveable",
        enabled=True,
        priority=100,
        match=RuleMatch(
            any=[
                MatchCondition(contains="Upp::Vector"),
                MatchCondition(regex=r"Moveable<.*>"),
                MatchCondition(regex=r"Pick\(\)"),
                MatchCondition(regex=r"static_assert.*Moveable")
            ],
            not_conditions=[
                MatchCondition(contains="already derives from Moveable")
            ]
        ),
        confidence=0.85,
        explanation="U++ Vector requires element types to be Moveable; element relocation happens.",
        actions=[
            RuleAction(
                type="hint",
                text="If storing type T in Upp::Vector<T>, ensure T derives from Moveable<T> (or use a different container). Avoid pointers to elements."
            ),
            RuleAction(
                type="prompt_patch",
                model_preference=["qwen", "claude"],
                prompt_template="Given these diagnostics, update the code so that types stored in Upp::Vector<T> satisfy Moveable constraints..."
            )
        ],
        verify=RuleVerify(expect_signature_gone=True)
    )

    # Create the rulebook
    rulebook = Rulebook(
        version=1,
        name="upp-cpp-fixes",
        description="Fixes for common U++ and template errors",
        rules=[rule]
    )

    # Save it
    save_rulebook("upp-cpp-fixes", rulebook)
    print("Created upp-cpp-fixes rulebook with U++ Vector/Moveable rule")

    # Also create the test rulebook with the same rule for testing
    test_rulebook = Rulebook(
        version=1,
        name="test-reactive-rules", 
        description="Test rulebook for reactive rules",
        rules=[rule]
    )
    
    save_rulebook("test-reactive-rules", test_rulebook)
    print("Created test-reactive-rules rulebook")


if __name__ == "__main__":
    create_sample_rulebook()