import { BaseApiResponseData } from "@/utils/type-declarations";
import { $api } from "../../utils/api";
import {
  handleProjectError,
  ImageNotFoundError,
  UnidentifiedError,
} from "../common-errors";

export interface ProductData {
  Product: {
    id: number;
    Name: string;
    Type: string;
    Details: {
      Description: string;
      Product_Details: {
        Features: string[];
      };
      Core_Characteristic: string;
      Competitive_Advantage: string;
      Benefit_Related_to_Hypothesis: string;
    };
    preferred: number;
  };
}

export type ProductListResponse = BaseApiResponseData<{
  project_id: number;
  products: ProductData[];
}>;

export type PreferredProductResponse = BaseApiResponseData<{
  project_id: number;
  product_id: number;
  preferred_product: ProductData;
}>;

export default {
  // servicio 4/18 de la fase 2 :  Choose one buyer that fits your hypothesis   4
  async generate(project_id: number): Promise<ProductListResponse> {
    try {
      const response = await $api<ProductListResponse>(
        "/v1/application/hiluca/project/product/generate",
        {
          method: "POST",
          body: {
            project_id,
          },
        },
      );

      return response;
    } catch (error: any) {
      handleProjectError(error);
      throw new UnidentifiedError();
    }
  },

  // servicio 5/18 de la fase 2 :  Select The Optimal Product For Your Hypothesis   5
  async setPreferred(
    project_id: number,
    product_id: number,
  ): Promise<PreferredProductResponse> {
    try {
      const response = await $api<PreferredProductResponse>(
        "/v1/application/hiluca/project/product/set_preferred",
        {
          method: "POST",
          body: {
            project_id: project_id,
            product_id: product_id,
          },
        },
      );

      return response;
    } catch (error: any) {
      handleProjectError(error);
      throw new UnidentifiedError();
    }
  },

  // Save Preferred Product
  // servicio 6/18 de la fase 2 :  Select The Optimal Product For Your Hypothesis   5
  async savePreferred(
    project_id: number,
    product: ProductData,
  ): Promise<ProductListResponse> {
    try {
      const response = await $api<ProductListResponse>(
        "/v1/application/hiluca/project/preferred_product",
        {
          method: "POST",
          body: {
            project_id: project_id,
            preferred_product: product,
          },
        },
      );

      return response;
    } catch (error: any) {
      handleProjectError(error);
      throw new UnidentifiedError();
    }
  },

  // Upload  Product Image
  // servicio 9/18 de la fase 2 :  Select The Optimal Product For Your Hypothesis   9
  async uploadImage(project_id: number, image: Blob): Promise<void> {
    // Create a form data to append the file
    const formData = new FormData();
    formData.append("file", image);

    try {
      await $api(`/v1/application/hiluca/project/${project_id}/product/image`, {
        method: "POST",
        body: formData,
      });
      return;
    } catch (error: any) {
      handleProjectError(error);
      throw new UnidentifiedError();
    }
  },

  async getImage(
    projectId: number,
    allowUndefined?: boolean,
  ): Promise<Blob | undefined> {
    try {
      const response = await $api(
        `/v1/application/hiluca/project/${projectId}/product/image`,
        {
          method: "GET",
          cache: "no-cache",
        },
      );

      return response as Blob;
    } catch (error: any) {
      if (allowUndefined) {
        return undefined;
      }

      handleProjectError(error);
      throw new ImageNotFoundError();
    }
  },
};
