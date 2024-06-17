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

    const slackBotFnRole = new cdk.aws_iam.Role(this, "SlackBotFnRole", {
      assumedBy: new cdk.aws_iam.ServicePrincipal("lambda.amazonaws.com"),
      managedPolicies: [
        cdk.aws_iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AWSLambdaBasicExecutionRole",
        ),
      ],
    });
    const aossIndexingPrincipalArn =
      cdk.aws_ssm.StringParameter.valueForStringParameter(
        this,
        "AossIndexingPrincipalArn",
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
            Principal: [
              slackBotFnRole.roleArn,
              aossIndexingPrincipalArn, // インデックス操作を行うプリンシパルのARN
            ],
          },
        ]),
      },
    );

    const aossIndexName = cdk.aws_ssm.StringParameter.valueForStringParameter(
      this,
      "AossIndexName",
    );
    const ragEnabled = cdk.aws_ssm.StringParameter.valueForStringParameter(
      this,
      "RagEnabled",
    );
    const slackBotToken = cdk.aws_ssm.StringParameter.valueForStringParameter(
      this,
      "SlackBotToken",
    );
    const slackSignSecret = cdk.aws_ssm.StringParameter.valueForStringParameter(
      this,
      "SlackSignSecret",
    );

    const slackBotFn = new cdk.aws_lambda.Function(this, "SlackBotFn", {
      code: cdk.aws_lambda.Code.fromAssetImage("../server"),
      handler: cdk.aws_lambda.Handler.FROM_IMAGE,
      architecture: cdk.aws_lambda.Architecture.ARM_64,
      runtime: cdk.aws_lambda.Runtime.FROM_IMAGE,
      memorySize: 1769, // 1vCPUフルパワー @see https://docs.aws.amazon.com/ja_jp/lambda/latest/dg/gettingstarted-limits.html
      timeout: cdk.Duration.minutes(15),
      environment: {
        AOSS_ENDPOINT_URL: knowledgeBaseCollection.attrCollectionEndpoint,
        AOSS_INDEX_NAME: aossIndexName,
        RAG_ENABLED: ragEnabled,
        SLACK_BOT_TOKEN: slackBotToken,
        SLACK_SIGNING_SECRET: slackSignSecret,
      },
      role: slackBotFnRole,
    });
    slackBotFn.addFunctionUrl({
      authType: cdk.aws_lambda.FunctionUrlAuthType.NONE,
      cors: {
        allowedMethods: [cdk.aws_lambda.HttpMethod.ALL],
        allowedOrigins: ["*"],
      },
    });
    slackBotFn.addToRolePolicy(
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

    // Slack BoltのLazyリスナーでは、内部的に自身のLambda関数を呼び出すためInvokeFunction権限が必要
    // resourcesにslackBotFn.functionArnを指定すると循環参照が発生してしまうため、いったん緩く設定する
    slackBotFn.addToRolePolicy(
      new cdk.aws_iam.PolicyStatement({
        effect: cdk.aws_iam.Effect.ALLOW,
        actions: ["lambda:InvokeFunction"],
        resources: ["*"],
      }),
    );
  }
}
