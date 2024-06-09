import * as apprunner from "@aws-cdk/aws-apprunner-alpha";
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export class MainStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const knowledgeBaseCollection =
      new cdk.aws_opensearchserverless.CfnCollection(
        this,
        "KnowledgeBaseCollection",
        {
          name: "knowledge-base",
          type: "VECTORSEARCH",
          standbyReplicas: "DISABLED",
        },
      );

    const knowledgeBaseCollectionEncryptionPolicy =
      new cdk.aws_opensearchserverless.CfnSecurityPolicy(
        this,
        "KnowledgeBaseCollectionEncryptionPolicy",
        {
          name: "knowledge-base-encryption-policy",
          type: "encryption",
          policy: JSON.stringify({
            Rules: [
              {
                ResourceType: "collection",
                Resource: [`collection/${knowledgeBaseCollection.name}`],
              },
            ],
            AWSOwnedKey: true,
          }),
        },
      );

    // NOTE: コレクションを作成する前に、コレクションの名前と一致するリソースパターンを含む暗号化ポリシーを作成しておく必要がある
    // 暗号化ポリシー作成後にコレクションが作成されるように依存関係を設定する
    // @see https://docs.aws.amazon.com/ja_jp/opensearch-service/latest/developerguide/serverless-manage.html#serverless-create
    // @see https://docs.aws.amazon.com/ja_jp/opensearch-service/latest/developerguide/serverless-encryption.html
    knowledgeBaseCollection.addDependency(
      knowledgeBaseCollectionEncryptionPolicy,
    );

    new cdk.aws_opensearchserverless.CfnSecurityPolicy(
      this,
      "KnowledgeBaseCollectionNetworkPolicy",
      {
        name: "knowledge-base-network-policy",
        type: "network",
        policy: JSON.stringify([
          {
            Rules: [
              {
                ResourceType: "collection",
                Resource: [`collection/${knowledgeBaseCollection.name}`],
              },
              {
                ResourceType: "dashboard",
                Resource: [`collection/${knowledgeBaseCollection.name}`],
              },
            ],
            AllowFromPublic: true,
          },
        ]),
      },
    );

    const serverServiceInstanceRole = new cdk.aws_iam.Role(
      this,
      "ServerServiceInstanceRole",
      {
        assumedBy: new cdk.aws_iam.ServicePrincipal(
          "tasks.apprunner.amazonaws.com",
        ),
      },
    );

    new cdk.aws_opensearchserverless.CfnAccessPolicy(
      this,
      "KnowledgeBaseCollectionAccessPolicy",
      {
        name: "knowledge-base-access-policy",
        type: "data",
        policy: JSON.stringify([
          {
            Rules: [
              {
                ResourceType: "collection",
                Resource: [`collection/${knowledgeBaseCollection.name}`],
                Permission: ["aoss:*"],
              },
              {
                ResourceType: "index",
                Resource: [`index/${knowledgeBaseCollection.name}/*`],
                Permission: ["aoss:*"],
              },
            ],
            Principal: [serverServiceInstanceRole.roleArn],
          },
        ]),
      },
    );

    const slackBotToken = cdk.aws_ssm.StringParameter.valueForStringParameter(
      this,
      "SlackBotToken",
    );
    const slackSignSecret = cdk.aws_ssm.StringParameter.valueForStringParameter(
      this,
      "SlackSignSecret",
    );
    const aossIndexName = cdk.aws_ssm.StringParameter.valueForStringParameter(
      this,
      "AossIndexName",
    );

    const serverService = new apprunner.Service(this, "ServerService", {
      source: apprunner.Source.fromAsset({
        imageConfiguration: {
          port: 3000,
          environmentVariables: {
            AOSS_ENDPOINT_URL: knowledgeBaseCollection.attrCollectionEndpoint,
            AOSS_INDEX_NAME: aossIndexName,
            SLACK_BOT_TOKEN: slackBotToken,
            SLACK_SIGNING_SECRET: slackSignSecret,
          },
        },
        asset: new cdk.aws_ecr_assets.DockerImageAsset(this, "ImageAsset", {
          directory: "../server",
          platform: cdk.aws_ecr_assets.Platform.LINUX_AMD64,
        }),
      }),
      cpu: apprunner.Cpu.ONE_VCPU,
      memory: apprunner.Memory.TWO_GB,
      healthCheck: apprunner.HealthCheck.tcp({}),
      instanceRole: serverServiceInstanceRole,
      autoDeploymentsEnabled: true,
    });
    serverService.addToRolePolicy(
      new cdk.aws_iam.PolicyStatement({
        effect: cdk.aws_iam.Effect.ALLOW,
        actions: [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "aoss:*",
        ],
        resources: ["*"],
      }),
    );
  }
}
