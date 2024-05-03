import * as apprunner from "@aws-cdk/aws-apprunner-alpha";
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export class MainStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const slackBotToken = cdk.aws_ssm.StringParameter.valueForStringParameter(
      this,
      "SlackBotToken",
    );
    const slackSignSecret = cdk.aws_ssm.StringParameter.valueForStringParameter(
      this,
      "SlackSignSecret",
    );

    new apprunner.Service(this, "ServerService", {
      source: apprunner.Source.fromAsset({
        imageConfiguration: {
          port: 3000,
          environmentVariables: {
            SLACK_BOT_TOKEN: slackBotToken,
            SLACK_SIGNING_SECRET: slackSignSecret,
          },
        },
        asset: new cdk.aws_ecr_assets.DockerImageAsset(this, "ImageAsset", {
          directory: "../server",
          platform: cdk.aws_ecr_assets.Platform.LINUX_AMD64,
        }),
      }),
      healthCheck: apprunner.HealthCheck.tcp({}),
      autoDeploymentsEnabled: true,
    });
  }
}
