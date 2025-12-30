<div align="center">
  <img src="docs/assets/images/project-banner.png" alt="Project-Banner" />
  <h3>Snapfire</h3>
  <p>Server-to-Server latency observability project</p>

  <a href="https://github.com/thuyetbao/snapfire">
    <img src="https://img.shields.io/badge/project--snapfire-0.6.35-darkblue?logo=fantom&logoColor=white" alt="Project">
  </a>
  <br>
  <a href="https://cloud.google.com/">
    <img src="https://img.shields.io/badge/cloud-google--cloud--platform-blue?logo=google-cloud&logoColor=white" alt="Google Cloud Platform">
  </a>
  <br>
  <a href="https://www.terraform.io/">
    <img src="https://img.shields.io/badge/terraform-1.10.5-darkorange?logo=terraform&logoColor=white" alt="Terraform">
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/python-3.12-darkorange?logo=python&logoColor=white" alt="Python">
  </a>
  <br>
  <a href="https://pre-commit.com/" target="_blank">
    <img src="https://img.shields.io/badge/pre--commit-enabled-teal?logo=pre-commit" alt="pre-commit enabled">
  </a>
  <a href="https://docs.pydantic.dev/latest/" target="_blank">
    <img src="https://img.shields.io/badge/data--model-pydantic-teal?logo=pydantic" alt="Data validation with pydantic">
  </a>
</div>

---

**Features:**

- Measure probe–target network latency via four methods: ICMP, UDP, TCP, and HTTP.

- Provision infrastructure (compute, firewall, iam) on Google Cloud Platform using infrastructure-as-code.

- Deploy daemon-based services across cloud virtual machines.

- Document architecture, setup, metrics interpretation, assumptions, and tradeoffs.

> [!NOTE]
> For solution design concepts, reference to: [docs/sad.md](docs/sad.md)
>
> For project workflow, reference to: [docs/workflow.md](docs/workflow.md)

**Documentation:**

The project has been document at folder [docs](docs/)
and live at [endpoint documentation (local)][endpoint-origin-url-documentation]

**Code Storage**:

Repository: [GitHub > Repository::`snapfire`][github-project-origin-url]

**Releases**:

Releases: [GitHub > Repository::`snapfire` > Releases][github-project-releease-url]

**Contributors**:

- Thuyet Bao [trthuyetbao@gmail.com](mailto:trthuyetbao@gmail.com) [Author]

**Disclaimer:**

This project used AI tools for code pairing, base generation, and documentation support.
All designs, implementations, and results were **reviewed and validated by the author**.

AI assistance was provided via **ChatGPT with Windsurf**.
The author remains fully responsible for all technical decisions and outcomes.

<!-- Bundle URL -->

[github-project-origin-url]: https://github.com/thuyetbao/snapfire.git
[github-project-releease-url]: https://github.com/thuyetbao/snapfire.git/-/releases
[endpoint-origin-url-documentation]: http://localhost:7777
