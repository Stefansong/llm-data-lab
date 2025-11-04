declare module "diff" {
  export interface ApplyPatchOptions {
    fuzzFactor?: number;
  }

  export function applyPatch(
    source: string,
    patch: string,
    options?: ApplyPatchOptions
  ): string | false;

  export function createTwoFilesPatch(
    oldFileName: string,
    newFileName: string,
    oldStr: string,
    newStr: string,
    oldHeader?: string,
    newHeader?: string,
    options?: { context?: number }
  ): string;
}
