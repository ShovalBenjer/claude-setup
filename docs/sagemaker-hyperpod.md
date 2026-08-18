

# Amazon SageMaker HyperPod
<a name="sagemaker-hyperpod"></a>

SageMaker HyperPod helps you provision resilient clusters for running machine learning (ML) workloads and developing state-of-the-art models such as large language models (LLMs), diffusion models, and foundation models (FMs). It accelerates development of FMs by removing undifferentiated heavy-lifting involved in building and maintaining large-scale compute clusters powered by thousands of accelerators such as AWS Trainium and NVIDIA A100 and H100 Graphical Processing Units (GPUs). When accelerators fail, the resiliency features of SageMaker HyperPod monitor the cluster instances automatically detect and replace the faulty hardware on the fly so that you can focus on running ML workloads.

To get started, check [Prerequisites for using SageMaker HyperPod](sagemaker-hyperpod-prerequisites.md), set up [AWS Identity and Access Management for SageMaker HyperPod](sagemaker-hyperpod-prerequisites-iam.md), and choose one of the following orchestrator options supported by SageMaker HyperPod.

**Slurm support in SageMaker HyperPod**

SageMaker HyperPod provides support for running machine learning workloads on resilient clusters by integrating with Slurm, an open-source workload manager. Slurm support in SageMaker HyperPod enables seamless cluster orchestration through Slurm cluster configuration, allowing you to set up head, login, and worker nodes on the SageMaker HyperPod clusters This integration also facilitates Slurm-based job scheduling for running ML workloads on the cluster, as well as direct access to cluster nodes for job scheduling. With HyperPod's lifecycle configuration support, you can customize the computing environment of the clusters to meet your specific requirements. Additionally, by leveraging the Amazon SageMaker AI distributed training libraries, you can optimize the clusters' performance on AWS computing and network resources. To learn more, see [Orchestrating SageMaker HyperPod clusters with Slurm](sagemaker-hyperpod-slurm.md). 

**Amazon EKS support in SageMaker HyperPod**

SageMaker HyperPod also integrates with Amazon EKS to enable large-scale training of foundation models on long-running and resilient compute clusters. This allows cluster admin users to provision HyperPod clusters and attach them to an EKS control plane, enabling dynamic capacity management, direct access to cluster instances, and resiliency capabilities. For data scientists, Amazon EKS support in HyperPod allows running containerized workloads for training foundation models, inference on the EKS cluster, and leveraging the job auto-resume capability for Kubeflow PyTorch training. The architecture involves a 1-to-1 mapping between an EKS cluster (control plane) and a HyperPod cluster (worker nodes) within a VPC, providing a tightly integrated solution for running large-scale ML workloads. To learn more, see [Orchestrating SageMaker HyperPod clusters with Amazon EKS](sagemaker-hyperpod-eks.md).

**UltraServers with HyperPod**

HyperPod with UltraServers delivers AI computing power by integrating NVIDIA superchips into a cohesive, high-performance infrastructure. Each NVL72 UltraServer combines 18 instances with 72 NVIDIA Blackwell GPUs interconnected via NVLink, enabling faster inference and faster training performance compared to previous generation instances. This architecture is particularly valuable for organizations working with trillion-parameter foundation models, as the unified GPU memory allows entire models to remain within a single NVLink domain, eliminating cross-node networking bottlenecks. HyperPod enhances this hardware advantage with intelligent topology-aware scheduling that optimizes workload placement, automatic instance replacement to minimize disruptions, and flexible deployment options that support both dedicated and shared resource configurations. For teams pushing the boundaries of model size and performance, this integration provides the computational foundation needed to train and deploy the most advanced AI models with unprecedented efficiency.

SageMaker HyperPod automatically optimizes instance placement across your UltraServers. By default, HyperPod prioritizes all instances in one UltraServer before using a different one. For example, if you want 14 instances and have 2 UltraServers in your plan, SageMaker AI uses all of the instances in the first UltraServer. If you want 20 instances, SageMaker AI uses all 18 instances in the first UltraServer and then uses 2 more from the second.

## AWS Regions supported by SageMaker HyperPod
<a name="sagemaker-hyperpod-available-regions"></a>

SageMaker HyperPod is available in the following AWS Regions. 
+ us-east-1
+ us-east-2
+ us-west-1
+ us-west-2
+ eu-central-1
+ eu-north-1
+ eu-west-1
+ eu-west-2
+ eu-south-2
+ ap-south-1
+ ap-south-2
+ ap-southeast-1
+ ap-southeast-2
+ ap-southeast-3
+ ap-southeast-4
+ ap-northeast-1
+ ap-northeast-2
+ sa-east-1

**Topics**
+ [AWS Regions supported by SageMaker HyperPod](#sagemaker-hyperpod-available-regions)
+ [Amazon SageMaker HyperPod quickstart](sagemaker-hyperpod-quickstart.md)
+ [Prerequisites for using SageMaker HyperPod](sagemaker-hyperpod-prerequisites.md)
+ [AWS Identity and Access Management for SageMaker HyperPod](sagemaker-hyperpod-prerequisites-iam.md)
+ [Customer managed AWS KMS key encryption for SageMaker HyperPod](smcluster-cmk.md)
+ [SageMaker HyperPod recipes](sagemaker-hyperpod-recipes.md)
+ [Orchestrating SageMaker HyperPod clusters with Slurm](sagemaker-hyperpod-slurm.md)
+ [Orchestrating SageMaker HyperPod clusters with Amazon EKS](sagemaker-hyperpod-eks.md)
+ [Using topology-aware scheduling in Amazon SageMaker HyperPod](sagemaker-hyperpod-topology.md)
+ [Deploying models on Amazon SageMaker HyperPod](sagemaker-hyperpod-model-deployment.md)
+ [SageMaker HyperPod cluster events reference](sagemaker-hyperpod-cluster-events-reference.md)
+ [HyperPod in Studio](sagemaker-hyperpod-studio.md)
+ [SageMaker HyperPod references](sagemaker-hyperpod-ref.md)
+ [Amazon SageMaker HyperPod release notes](sagemaker-hyperpod-release-notes.md)
+ [Amazon SageMaker HyperPod AMI](sagemaker-hyperpod-release-ami.md)