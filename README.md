# **Integrated Patient System with AI Clinical Assistant**

## **Overview**

This project is a full-stack Patient Records and Clinical Assistant portal designed to unify fragmented hospital data systems into a single, intelligent interface for doctors. Hospitals typically operate multiple independent databases for MRI, CT scans, ECG, blood tests, X-rays, and treatments. This system integrates all those sources into one portal and augments them with an LLM-powered AI assistant (DocAssist) that helps doctors query, analyze, and understand patient data efficiently.

The platform is built with React (frontend), FastAPI (backend), and MongoDB (database), and supports both text-based and multimodal AI analysis (PDFs, medical images).

⸻

## **Problem Statement**

In real hospital environments, patient data is scattered across multiple systems, forcing doctors to manually search, interpret, and correlate reports under time pressure. This fragmentation increases cognitive load, delays decisions, and raises the risk of oversight. Existing systems focus on storage and retrieval but lack intelligent, conversational clinical support.

⸻


## **Solution Overview**

This project consolidates all patient records into a single portal and introduces DocAssist, an AI-powered clinical assistant that behaves like a “clinical Siri” for doctors. Instead of manually browsing reports, doctors can ask natural language questions, upload reports, and receive grounded, context-aware explanations based strictly on the patient’s actual medical records.

DocAssist does not replace clinical judgment; it supports decision-making by summarizing findings, highlighting abnormalities, and providing clear clinical context.

⸻

## **Key Features**

	•	Unified patient portal integrating MRI, CT, ECG, Blood Test, X-Ray, and Treatment records
	•	Intelligent patient-aware search with strict validation and confirmation workflow
	•	DocAssist AI Clinical Assistant powered by real LLMs
	•	Natural language clinical queries grounded in patient data
	•	Multimodal analysis of uploaded PDFs and medical images (JPG/PNG)
	•	Conversational memory to preserve clinical context across interactions
	•	Modular backend architecture supporting both Emergent LLM and direct OpenAI/Gemini APIs
	•	Designed for secure, local deployment within hospital environments

⸻

## **AI & Clinical Intelligence**

DocAssist is implemented as a true LLM-driven assistant, not a keyword search or static summarizer. It:
	•	Identifies relevant records dynamically based on the doctor’s query
	•	Analyzes abnormal values, impressions, and trends across reports
	•	Explains findings in clear, clinician-friendly language
	•	Maintains continuity across follow-up questions
	•	Supports multimodal reasoning for scanned reports and images

The system currently supports:
	•	Emergent LLM integration (platform runtime)
	•	Direct OpenAI/Gemini APIs for local execution
	•	Rule-based fallbacks when AI services are unavailable

⸻

## **Architecture**

	•	Frontend: React, modular components, no UI redesign during AI integration
	•	Backend: FastAPI with clearly separated AI, data, and routing layers
	•	Database: MongoDB collections per report type
	•	AI Layer: Pluggable LLM interface (Emergent or direct APIs)
	•	Security Model: Local execution supported for data privacy# Here are your Instructions

_____

## **Branching Strategy**

	•	main: Stable base system
	•	feature/deep-search: Patient-aware AI workflow
	•	feature/demo-data-with-APIKEY: Full AI-enabled demo with real LLMs and sample data

All AI enhancements were implemented without breaking existing UI or workflows, following strict incremental changes.

⸻

## **Future Work**

	•	Train and deploy a secure organization-specific local clinical model
	•	Fine-tune LLMs on anonymized hospital data
	•	Role-based access control and audit logging
	•	On-premise inference for regulated healthcare environments
	•	Integration with hospital EHR standards (FHIR)

_____

## **Impact**

This system demonstrates how LLMs can be safely embedded into healthcare workflows to reduce cognitive load, improve data accessibility, and support faster, more informed clinical decisions — without disrupting existing hospital operations.
