# simple-cloud-pickup

FilaFácil Logística, Cloud Fundamentals module. A small web application where the technical team registers, lists, and updates pickups. The application runs on Cloudflare Workers. Every save rewrites one JSON file in Cloudflare R2.

## 1. The problem and the solution

The local pickup system already worked on the developer's machine. The team needs to open it from somewhere else, and a file the application produces needs to live in object storage rather than on that machine.

This project is that application. It is a new program. It does not change the earlier FilaFácil projects. Opening the public URL shows the page. Each registration or status change reads `pickups.json` from the bucket, updates the list, and writes the file back.

## 2. Technologies

- TypeScript, no runtime framework
- Cloudflare Workers (the application)
- Cloudflare R2 (the object storage)
- Wrangler (local run and deploy)
- Node.js 22+ for the tests (`node:test`)

The handler stays small on purpose. The Workers free plan allows 10 milliseconds of CPU time per request. Waiting for R2 does not count. Parsing a large page framework would.

## 3. Project structure

```
projects/junior/simple-cloud-pickup/
├── wrangler.toml          # worker name, object key, R2 binding (no secrets)
├── package.json           # dev, deploy, test, check
├── src/
│   ├── pickups.ts         # validation and the pickup list rules
│   ├── store.ts           # read and write pickups.json in R2
│   ├── page.ts            # the HTML page
│   └── index.ts           # the Worker entry point
├── tests/
└── README.md
```

## 4. How to run

```bash
cd projects/junior/simple-cloud-pickup
npm install
npm run dev
```

`npm run dev` starts Wrangler on your machine and simulates R2 in `.wrangler/`. That directory is gitignored. The simulation does not read or write the real bucket. Open the local URL Wrangler prints, register a pickup, and update its status.

Deploying to Cloudflare is section 8.

### Tests

```bash
npm test
npm run check
```

The tests cover the rules and the request flow with an in-memory bucket. They do not call Cloudflare.

## 5. How to use

The interface is in Brazilian Portuguese. Stored values stay in English, as in the local system.

| Field | Stored value | Shown on the page |
| --- | --- | --- |
| `customer_name` | text | Nome do cliente |
| `address` | text | Endereço |
| `package_count` | integer greater than zero | Pacotes |
| `priority` | `low`, `medium`, `high` | Baixa, Média, Alta |
| `status` | `pending`, `in_transit`, `completed` | Pendente, Em rota, Concluída |

A new pickup receives the next id (highest existing id + 1, or 1) and starts as `pending`. Name and address cannot be blank. Updating a status rewrites the same file. An unknown id, or a status equal to the current one, changes nothing.

There is no login. Anyone with the URL can register a pickup. Use fictitious data.

## 6. Data

| | |
| --- | --- |
| Service | Cloudflare R2 |
| Bucket | `filafacil-pickups` |
| Object | `pickups.json` |
| When it is written | After every successful registration or status update |
| When it is missing | The page opens with an empty list and creates the object on the first save |
| When the object is not valid JSON | The page shows an error and does not overwrite the object |

The Worker receives the bucket through a binding named `PICKUPS`. A binding is permission granted by the platform at deploy time. The code does not contain an access key, and `wrangler.toml` does not contain one either.

R2 is S3-compatible object storage. This project uses the Workers binding rather than the S3 API, so there is no key to rotate inside the repository.

A stored file looks like this:

```json
[
  {
    "id": 1,
    "customer_name": "Maria Souza",
    "address": "Rua das Flores, 123",
    "package_count": 3,
    "priority": "high",
    "status": "pending"
  }
]
```

Status uses `pending`, `in_transit` and `completed`, the same set as Module 1.

## 7. Service model

The application is deployed as **PaaS**. Cloudflare runs the runtime, the HTTPS certificate, and the public URL. The repository supplies the program and the configuration. Nobody in this project administers an operating system.

| Model | What it would mean here | Decision |
| --- | --- | --- |
| IaaS | A virtual machine, such as the Hostinger VPS in São Paulo or an AWS EC2 instance. The team would install the system, keep a process running, and open a port. The disk of that machine is not object storage. | Not used. It spends the module on the operating system, and a machine left running is a paid resource. |
| PaaS | Publish the program. The platform starts it when a request arrives and serves it on a URL. | **Used.** Workers matches the size of this module and stays on the free plan. |
| SaaS | Adopt a finished product and only configure it. | Not used. No finished product is this pickup system. |

## 8. Deploy

You need a Cloudflare account that already shows **R2** and **Workers & Pages** in the dashboard. Workers on the free plan needs nothing else. R2, the first time, asks you to add the R2 subscription under **Storage & databases → R2 → Overview**. That checkout can ask for a card. It does not switch Workers to the paid plan. Stay inside the free allowance in section 10 and the expected bill is R$ 0. Do not enable Workers Paid.

In **R2**, create one bucket, or let the command below create it:

| Setting | Value |
| --- | --- |
| Name | `filafacil-pickups` |
| Location | Eastern North America (`enam`) |
| Storage class | Standard |

Leave public access off. Do not create an API token. The Worker uses the `PICKUPS` binding, not a key.

In **Workers**, do not create an empty function. `npm run deploy` creates the Worker `simple-cloud-pickup` and attaches the binding. `OBJECT_KEY` is already `pickups.json` in `wrangler.toml`. Leave that file as it is. After the bucket command, Wrangler prints the binding snippet again. On a TOML config it does not rewrite the file.

From this project, after `npm install`:

```bash
npx wrangler login
npx wrangler r2 bucket create filafacil-pickups --location enam
npm run deploy
```

`npx wrangler login` opens a browser and stores the token in Wrangler's own directory, outside this repository. On the first deploy, Wrangler may ask for the account's `workers.dev` subdomain. Pick any name. The command then prints the public URL, `https://simple-cloud-pickup.<that-name>.workers.dev`. The platform provides HTTPS. A custom domain is not required.

Deploy again with `npm run deploy` after a code change. The bucket and the file survive a new deploy.

## 9. Region and zone

Two placements are involved, and only one of them is chosen by us.

**Requests.** Workers runs on Cloudflare's edge. A person opening the page from Brazil is served from the nearest point of presence, São Paulo (GRU). We do not pin the Worker to a single city. The platform chooses the site per request.

**The file.** The bucket is created with the location hint `enam` (Eastern North America). R2 has no location in Brazil. The hints are Western and Eastern North America, Western and Eastern Europe, Asia-Pacific, and Oceania. Eastern North America is the closest of those to São Paulo. A location hint is best effort: Cloudflare may still place the bucket according to where the create request came from, and the hint is applied only the first time that bucket name is created.

**Zone.** Cloudflare does not offer an availability zone for Workers or for R2. There is no value such as `sa-east-1a` to select. This is a limit of the platform, recorded here rather than invented.

## 10. Cost

Prices below were taken from Cloudflare's public pages in November 2026. A team using this page stays inside the free allowances, so the expected monthly cost is **R$ 0**. Nothing in this project starts a paid plan.

| Resource | Free allowance | If the allowance is exceeded |
| --- | --- | --- |
| Workers requests | 100,000 per day | The free plan stops the Worker for the rest of the day (error 1027). It does not start billing. |
| Workers CPU | 10 milliseconds per request | A request that stays over the limit fails with error 1102. Waiting for R2 does not consume this budget. |
| R2 storage | 10 GB-month | US$ 0.015 per GB-month |
| R2 writes (Class A) | 1 million per month | US$ 4.50 per million |
| R2 reads (Class B) | 10 million per month | US$ 0.36 per million |
| R2 egress | Free | Free |

One page view reads the object once. One save reads it and writes it once. Thousands of those operations remain inside the table above.

The paid Workers plan starts at US$ 5 per month and raises the CPU limit to 30 seconds per request. This module does not need it. Do not enable it unless a real limit is hit. Leaving a paid plan on, unused, is the cost this module asks us to avoid.

## 11. Limits and how it could scale

| Limit | What happens | A later step, outside this module |
| --- | --- | --- |
| One JSON object | Two saves at the same time: the last write replaces the file. A pickup from the earlier save can disappear. | One object per pickup, or a write that fails when the object's version changed. |
| 10 ms of CPU | A very large file could make parsing the JSON exceed the free limit. The request fails; the bucket is unchanged if the failure happens before the write. | Split the file, or move the Worker to the paid plan. |
| 100,000 requests per day | The free plan rejects further requests until the next day. | The paid plan includes 10 million requests per month. |
| No availability zone | The platform places the request and the file. We cannot pin a zone. | A provider that exposes zones, such as AWS `sa-east-1`, if a named zone becomes a requirement. |
| No login | Anyone with the URL can change the list. | Put the Worker behind Cloudflare Access. |

Workers already runs more copies when more people open the page. The part that does not scale is the single shared file.

## 12. Credentials

- `npx wrangler login` keeps the token outside the repository.
- `.dev.vars` and `.wrangler/` are gitignored.
- `wrangler.toml` holds the worker name, the object key, and the bucket binding. Those are not secrets.
- The R2 binding replaces an access key. Do not create an R2 API token for this project and do not paste one into the code.

## 13. Restrictions

Fictitious data only. No login. Stay on the Workers free plan and do not enable Workers Paid. The repository holds no API token. Credential details are in section 12.

## 14. Author

João França
