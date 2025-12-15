"""
Confidence scoring system for Maestro conversion runs.
"""
import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
import statistics

@dataclass
class ConfidenceScore:
    """Represents a confidence score with breakdown and evidence."""
    score: float
    grade: str
    breakdown: Dict[str, float]
    penalties_applied: List[Dict[str, Any]]
    recommendations: List[str]
    evidence_refs: List[str]
    run_id: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ScoringModel:
    """Configuration for the confidence scoring system."""
    version: str
    scale: List[int]
    weights: Dict[str, float]
    penalties: Dict[str, int]
    floors: Dict[str, int]
    thresholds: Dict[str, int] = None  # grade thresholds, default to standard

    def __post_init__(self):
        if self.thresholds is None:
            self.thresholds = {
                "A": 90,
                "B": 80,
                "C": 70,
                "D": 60,
                "F": 0
            }


class ConfidenceScorer:
    """Main class for computing confidence scores."""
    
    def __init__(self, model_path: str = None):
        self.model = self.load_model(model_path)
        self.default_model_path = model_path or ".maestro/convert/scoring/model.json"
    
    def load_model(self, model_path: str = None) -> ScoringModel:
        """Load the scoring model from file."""
        if model_path is None:
            model_path = ".maestro/convert/scoring/model.json"
        
        # Check if there's a repo-specific config that overrides the default
        repo_config_path = ".maestro/config.json"
        if os.path.exists(repo_config_path):
            try:
                with open(repo_config_path, 'r') as f:
                    repo_config = json.load(f)
                    if "confidence_model" in repo_config:
                        model_path = repo_config["confidence_model"]
            except (json.JSONDecodeError, KeyError):
                pass  # Use default model path
        
        # Load the model from the specified path
        if not os.path.exists(model_path):
            # Create default model if it doesn't exist
            self.create_default_model(model_path)
        
        try:
            with open(model_path, 'r') as f:
                model_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # Fallback: create and use default model
            self.create_default_model(model_path)
            with open(model_path, 'r') as f:
                model_data = json.load(f)
        
        return ScoringModel(**model_data)
    
    def create_default_model(self, model_path: str):
        """Create a default scoring model if file doesn't exist."""
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        default_model = {
            "version": "1.0",
            "scale": [0, 100],
            "weights": {
                "semantic_integrity": 0.35,
                "semantic_diff": 0.20,
                "drift_idempotency": 0.20,
                "checkpoints": 0.10,
                "open_issues": 0.10,
                "validation": 0.05
            },
            "penalties": {
                "semantic_low": 40,
                "semantic_medium": 15,
                "semantic_unknown": 8,
                "lost_concept": 3,
                "checkpoint_blocked": 10,
                "checkpoint_overridden": 6,
                "idempotency_failure": 20,
                "drift_detected": 15,
                "non_convergent": 25,
                "open_issue": 2,
                "validation_fail": 25
            },
            "floors": {
                "any_semantic_low": 30
            }
        }
        
        with open(model_path, 'w') as f:
            json.dump(default_model, f, indent=2)
    
    def compute_score(self, 
                     run_id: str,
                     artifacts_dir: str,
                     run_summary: Dict[str, Any] = None) -> ConfidenceScore:
        """Compute confidence score based on run artifacts."""
        if run_summary is None:
            run_summary = {}
        
        # Collect evidence from artifacts
        evidence = self.collect_evidence(artifacts_dir)
        
        # Calculate base score from components
        base_score = self.calculate_base_score(evidence)

        # Apply floors to determine maximum possible score
        max_possible_score = base_score
        floor_penalty_applied = 0
        if evidence.get("semantic_low", 0) > 0 and "any_semantic_low" in self.model.floors:
            floor_value = self.model.floors["any_semantic_low"]
            if max_possible_score > floor_value:
                floor_penalty_applied = max_possible_score - floor_value
                max_possible_score = floor_value

        # Apply penalties
        penalties_applied = []
        score_after_penalties = base_score  # Start with base score before floor enforcement
        for penalty_name, penalty_value in self.model.penalties.items():
            if penalty_name in evidence and evidence[penalty_name] > 0:
                count = evidence[penalty_name] if isinstance(evidence[penalty_name], (int, float)) else 1
                penalty_total = penalty_value * count
                score_after_penalties -= penalty_total
                penalties_applied.append({
                    "penalty": penalty_name,
                    "value": penalty_total,
                    "count": count,
                    "evidence_ref": evidence.get(f"{penalty_name}_evidence", "")
                })

        # Apply the floor constraint to the final score (after penalties)
        score_after_floors = min(score_after_penalties, max_possible_score)

        # If floor was applicable and we're capped by it, add floor penalty
        if evidence.get("semantic_low", 0) > 0 and "any_semantic_low" in self.model.floors:
            floor_value = self.model.floors["any_semantic_low"]
            if score_after_floors < score_after_penalties and score_after_penalties >= floor_value:
                penalties_applied.append({
                    "penalty": "floor_any_semantic_low",
                    "value": max(0, score_after_penalties - floor_value),
                    "count": 1,
                    "evidence_ref": "semantic integrity reports"
                })
            elif score_after_penalties < floor_value and base_score >= floor_value:
                # Floor would have applied, but penalties reduced below floor anyway
                penalties_applied.append({
                    "penalty": "floor_any_semantic_low",
                    "value": max(0, base_score - floor_value),
                    "count": 1,
                    "evidence_ref": "semantic integrity reports"
                })
        
        # Ensure score is within bounds
        final_score = max(self.model.scale[0], min(self.model.scale[1], score_after_floors))
        
        # Determine grade
        grade = self.get_grade(final_score)
        
        # Generate recommendations
        recommendations = self.generate_recommendations(evidence, penalties_applied)
        
        # Collect evidence references
        evidence_refs = self.collect_evidence_references(evidence)
        
        return ConfidenceScore(
            score=round(final_score, 2),
            grade=grade,
            breakdown=self.calculate_breakdown(evidence),
            penalties_applied=penalties_applied,
            recommendations=recommendations,
            evidence_refs=evidence_refs,
            run_id=run_id
        )
    
    def collect_evidence(self, artifacts_dir: str) -> Dict[str, Any]:
        """Collect evidence from various artifacts."""
        evidence = {
            # Default values - match the penalty names in the model
            "semantic_low": 0,
            "semantic_medium": 0,
            "semantic_unknown": 0,
            "lost_concept": 0,
            "checkpoint_blocked": 0,
            "checkpoint_overridden": 0,
            "idempotency_failure": 0,
            "drift_detected": 0,
            "non_convergent": 0,
            "open_issue": 0,
            "validation_fail": 0,
            "total_semantic_issues": 0
        }
        
        # Look for semantic integrity results
        semantic_summary_path = os.path.join(artifacts_dir, "semantic_summary.json")
        if os.path.exists(semantic_summary_path):
            try:
                with open(semantic_summary_path, 'r') as f:
                    semantic_data = json.load(f)
                    evidence["semantic_low"] = semantic_data.get("low_confidence_count", 0)
                    evidence["semantic_medium"] = semantic_data.get("medium_confidence_count", 0)
                    evidence["semantic_unknown"] = semantic_data.get("unknown_count", 0)
                    evidence["total_semantic_issues"] = semantic_data.get("total_issues", 0)
            except (json.JSONDecodeError, KeyError):
                pass

        # Look for cross-repo semantic diff
        diff_report_path = os.path.join(artifacts_dir, "diff_report.json")
        if os.path.exists(diff_report_path):
            try:
                with open(diff_report_path, 'r') as f:
                    diff_data = json.load(f)
                    evidence["lost_concept"] = diff_data.get("lost_concepts", 0)
            except (json.JSONDecodeError, KeyError):
                pass

        # Look for drift and idempotency reports
        drift_report_path = os.path.join(artifacts_dir, "drift_report.json")
        if os.path.exists(drift_report_path):
            try:
                with open(drift_report_path, 'r') as f:
                    drift_data = json.load(f)
                    evidence["drift_detected"] = drift_data.get("drift_detected_count", 0)
                    evidence["idempotency_failure"] = drift_data.get("idempotency_failures", 0)
                    evidence["non_convergent"] = drift_data.get("non_convergent_count", 0)
            except (json.JSONDecodeError, KeyError):
                pass
        
        # Look for checkpoint data - match the penalty names in model exactly
        checkpoint_path = os.path.join(artifacts_dir, "checkpoint_report.json")
        if os.path.exists(checkpoint_path):
            try:
                with open(checkpoint_path, 'r') as f:
                    checkpoint_data = json.load(f)
                    evidence["checkpoint_blocked"] = checkpoint_data.get("checkpoint_blocked_count", 0)
                    evidence["checkpoint_overridden"] = checkpoint_data.get("checkpoint_overridden_count", 0)
            except (json.JSONDecodeError, KeyError):
                pass
        else:
            # Also check for alternative checkpoint reporting files
            # that might contain checkpoint information
            for filename in os.listdir(artifacts_dir):
                if "checkpoint" in filename and filename.endswith(".json"):
                    try:
                        with open(os.path.join(artifacts_dir, filename), 'r') as f:
                            file_data = json.load(f)
                            # Look for checkpoint-related keys in various formats
                            if "checkpoint_blocked_count" in file_data:
                                evidence["checkpoint_blocked"] = file_data["checkpoint_blocked_count"]
                            elif "blocked" in file_data:
                                evidence["checkpoint_blocked"] = file_data["blocked"]

                            if "checkpoint_overridden_count" in file_data:
                                evidence["checkpoint_overridden"] = file_data["checkpoint_overridden_count"]
                            elif "overridden" in file_data:
                                evidence["checkpoint_overridden"] = file_data["overridden"]
                    except (json.JSONDecodeError, KeyError):
                        pass
        
        # Look for open issues
        open_issues_path = os.path.join(artifacts_dir, "open_issues.json")
        if os.path.exists(open_issues_path):
            try:
                with open(open_issues_path, 'r') as f:
                    issues_data = json.load(f)
                    evidence["open_issue"] = len(issues_data.get("issues", []))
            except (json.JSONDecodeError, KeyError):
                pass

        # Look for validation results
        validation_path = os.path.join(artifacts_dir, "validation_report.json")
        if os.path.exists(validation_path):
            try:
                with open(validation_path, 'r') as f:
                    validation_data = json.load(f)
                    evidence["validation_fail"] = validation_data.get("failed_count", 0)
            except (json.JSONDecodeError, KeyError):
                pass
        
        return evidence
    
    def calculate_base_score(self, evidence: Dict[str, Any]) -> float:
        """Calculate the base score based on weighted components."""
        weights = self.model.weights

        # Calculate component scores (scale to 0-100)
        semantic_score = max(0, 100 - (evidence["semantic_low"] * 5 +
                                      evidence["semantic_medium"] * 2 +
                                      evidence["semantic_unknown"] * 1))

        semantic_diff_score = max(0, 100 - (evidence["lost_concept"] * 10))

        drift_idempotency_score = max(0, 100 - (evidence["drift_detected"] * 10 +
                                               evidence["idempotency_failure"] * 20 +
                                               evidence["non_convergent"] * 15))

        checkpoint_score = max(0, 100 - (evidence["checkpoint_blocked"] * 20 +
                                        evidence["checkpoint_overridden"] * 10))

        open_issues_score = max(0, 100 - (evidence["open_issue"] * 5))

        validation_score = max(0, 100 - (evidence["validation_fail"] * 30))

        # Weighted total - components are 0-100, weights sum to 1, so result is 0-100
        base_score = (
            semantic_score * weights.get("semantic_integrity", 0.35) +
            semantic_diff_score * weights.get("semantic_diff", 0.20) +
            drift_idempotency_score * weights.get("drift_idempotency", 0.20) +
            checkpoint_score * weights.get("checkpoints", 0.10) +
            open_issues_score * weights.get("open_issues", 0.10) +
            validation_score * weights.get("validation", 0.05)
        )  # No need to multiply by 100 since weights sum to 1 and scores are 0-100

        return min(100, max(0, base_score))
    
    def calculate_breakdown(self, evidence: Dict[str, Any]) -> Dict[str, float]:
        """Calculate score breakdown by component."""
        # Calculate component scores
        semantic_score = max(0, 100 - (evidence["semantic_low"] * 5 +
                                      evidence["semantic_medium"] * 2 +
                                      evidence["semantic_unknown"] * 1))

        semantic_diff_score = max(0, 100 - (evidence["lost_concept"] * 10))

        drift_idempotency_score = max(0, 100 - (evidence["drift_detected"] * 10 +
                                               evidence["idempotency_failure"] * 20 +
                                               evidence["non_convergent"] * 15))

        checkpoint_score = max(0, 100 - (evidence["checkpoint_blocked"] * 20 +
                                        evidence["checkpoint_overridden"] * 10))

        open_issues_score = max(0, 100 - (evidence["open_issue"] * 5))

        validation_score = max(0, 100 - (evidence["validation_fail"] * 30))

        return {
            "semantic_integrity": round(semantic_score, 2),
            "semantic_diff": round(semantic_diff_score, 2),
            "drift_idempotency": round(drift_idempotency_score, 2),
            "checkpoints": round(checkpoint_score, 2),
            "open_issues": round(open_issues_score, 2),
            "validation": round(validation_score, 2)
        }
    
    def get_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        thresholds = self.model.thresholds
        
        if score >= thresholds["A"]:
            return "A"
        elif score >= thresholds["B"]:
            return "B"
        elif score >= thresholds["C"]:
            return "C"
        elif score >= thresholds["D"]:
            return "D"
        else:
            return "F"
    
    def generate_recommendations(self,
                                evidence: Dict[str, Any],
                                penalties_applied: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on evidence and penalties."""
        recommendations = []

        if evidence["checkpoint_blocked"] > 0:
            recommendations.append(f"Resolve {evidence['checkpoint_blocked']} checkpoint(s) that require manual approval")

        if evidence["semantic_low"] > 0:
            recommendations.append(f"Address {evidence['semantic_low']} low-confidence semantic conversions")

        if evidence["open_issue"] > 0:
            recommendations.append(f"Resolve {evidence['open_issue']} open issues before finalizing")

        if evidence["validation_fail"] > 0:
            recommendations.append(f"Fix {evidence['validation_fail']} validation failures")

        if evidence["drift_detected"] > 0:
            recommendations.append(f"Review {evidence['drift_detected']} drift detections in semantic analysis")

        if evidence["idempotency_failure"] > 0:
            recommendations.append(f"Ensure idempotency by addressing {evidence['idempotency_failure']} failures")

        if not recommendations:
            recommendations.append("Overall confidence is high; no major issues detected")

        return recommendations
    
    def collect_evidence_references(self, evidence: Dict[str, Any]) -> List[str]:
        """Collect file paths to evidence artifacts."""
        refs = []
        
        # Check for various artifact files
        potential_refs = [
            "semantic_summary.json",
            "diff_report.json", 
            "drift_report.json",
            "checkpoint_report.json",
            "open_issues.json",
            "validation_report.json"
        ]
        
        # For this implementation, we'll return the potential paths
        # In a real implementation, we'd check which files actually exist
        for ref in potential_refs:
            if os.path.exists(os.path.join(".", ref)):  # Simplified for now
                refs.append(ref)
        
        return refs

    def save_confidence_report(self, confidence_score: ConfidenceScore, output_dir: str):
        """Save confidence report in both JSON and Markdown formats."""
        os.makedirs(output_dir, exist_ok=True)
        
        # Save JSON report
        json_path = os.path.join(output_dir, "confidence.json")
        with open(json_path, 'w') as f:
            json.dump(asdict(confidence_score), f, indent=2)
        
        # Save Markdown report
        md_path = os.path.join(output_dir, "confidence.md")
        with open(md_path, 'w') as f:
            f.write(f"# Conversion Confidence Report\n\n")
            f.write(f"**Run ID:** {confidence_score.run_id}\n")
            f.write(f"**Score:** {confidence_score.score}\n")
            f.write(f"**Grade:** {confidence_score.grade}\n")
            f.write(f"**Generated:** {confidence_score.timestamp}\n\n")
            
            f.write("## Score Breakdown\n\n")
            for component, score in confidence_score.breakdown.items():
                f.write(f"- **{component.replace('_', ' ').title()}:** {score}\n")
            
            f.write("\n## Applied Penalties\n\n")
            if confidence_score.penalties_applied:
                for penalty in confidence_score.penalties_applied:
                    f.write(f"- **{penalty['penalty']}:** -{penalty['value']} points ({penalty['count']} instance(s))\n")
            else:
                f.write("No penalties applied.\n")
            
            f.write("\n## Recommendations\n\n")
            for rec in confidence_score.recommendations:
                f.write(f"- {rec}\n")
            
            f.write("\n## Evidence References\n\n")
            if confidence_score.evidence_refs:
                for ref in confidence_score.evidence_refs:
                    f.write(f"- {ref}\n")
            else:
                f.write("No evidence references available.\n")


class BatchConfidenceAggregator:
    """Handle aggregation of confidence scores across batch runs."""
    
    def __init__(self, scoring_model_path: str = None):
        self.scorer = ConfidenceScorer(scoring_model_path)
    
    def aggregate_scores(self, 
                       run_scores: List[ConfidenceScore], 
                       aggregation_method: str = "min") -> ConfidenceScore:
        """Aggregate multiple run scores into a single batch confidence score."""
        if not run_scores:
            return ConfidenceScore(
                score=0,
                grade="F",
                breakdown={},
                penalties_applied=[],
                recommendations=["No runs to aggregate"],
                evidence_refs=[]
            )
        
        # Extract scores based on the aggregation method
        scores = [s.score for s in run_scores]
        
        if aggregation_method == "min":
            final_score = min(scores)
            # Find the run with the minimum score for evidence
            min_run = next(s for s in run_scores if s.score == final_score)
        elif aggregation_method == "max":
            final_score = max(scores)
            min_run = next(s for s in run_scores if s.score == final_score)
        elif aggregation_method == "mean":
            final_score = statistics.mean(scores)
            min_run = run_scores[0]  # Use first as representative
        elif aggregation_method == "median":
            final_score = statistics.median(scores)
            min_run = run_scores[0]  # Use first as representative
        else:
            raise ValueError(f"Unknown aggregation method: {aggregation_method}")
        
        # Combine breakdowns by averaging
        combined_breakdown = {}
        for key in min_run.breakdown.keys():
            values = [s.breakdown.get(key, 0) for s in run_scores]
            combined_breakdown[key] = statistics.mean(values) if values else 0
        
        # Combine penalties
        all_penalties = []
        for score in run_scores:
            all_penalties.extend(score.penalties_applied)
        
        # Combine recommendations
        all_recommendations = []
        for score in run_scores:
            all_recommendations.extend(score.recommendations)
        
        # Extract unique recommendations
        unique_recommendations = list(set(all_recommendations))
        
        return ConfidenceScore(
            score=round(final_score, 2),
            grade=self.scorer.get_grade(final_score),
            breakdown={k: round(v, 2) for k, v in combined_breakdown.items()},
            penalties_applied=all_penalties,
            recommendations=unique_recommendations,
            evidence_refs=min_run.evidence_refs,  # Use evidence from representative run
            run_id=f"batch_agg_{aggregation_method}",
            timestamp=datetime.now().isoformat()
        )
    
    def save_batch_confidence_report(self, 
                                    confidence_score: ConfidenceScore, 
                                    output_dir: str):
        """Save batch confidence report in both JSON and Markdown formats."""
        os.makedirs(output_dir, exist_ok=True)
        
        # Save JSON report
        json_path = os.path.join(output_dir, "confidence.json")
        with open(json_path, 'w') as f:
            json.dump(asdict(confidence_score), f, indent=2)
        
        # Save Markdown report
        md_path = os.path.join(output_dir, "confidence.md")
        with open(md_path, 'w') as f:
            f.write(f"# Batch Conversion Confidence Report\n\n")
            f.write(f"**Aggregation Method:** {confidence_score.run_id.split('_')[2] if '_' in str(confidence_score.run_id) else 'unknown'}\n")
            f.write(f"**Score:** {confidence_score.score}\n")
            f.write(f"**Grade:** {confidence_score.grade}\n")
            f.write(f"**Generated:** {confidence_score.timestamp}\n\n")
            
            f.write("## Score Breakdown\n\n")
            for component, score in confidence_score.breakdown.items():
                f.write(f"- **{component.replace('_', ' ').title()}:** {score}\n")
            
            f.write("\n## Applied Penalties\n\n")
            if confidence_score.penalties_applied:
                penalty_counts = {}
                for penalty in confidence_score.penalties_applied:
                    p_name = penalty['penalty']
                    if p_name in penalty_counts:
                        penalty_counts[p_name] += 1
                    else:
                        penalty_counts[p_name] = 1
                
                for penalty, count in penalty_counts.items():
                    f.write(f"- **{penalty}:** occurred in {count} run(s)\n")
            else:
                f.write("No penalties applied.\n")
            
            f.write("\n## Recommendations\n\n")
            for rec in confidence_score.recommendations:
                f.write(f"- {rec}\n")