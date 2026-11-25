import Lake
open Lake DSL

package fourier_sqrtlog where
  leanOptions := #[
    ⟨`autoImplicit, false⟩,
    ⟨`relaxedAutoImplicit, false⟩
  ]

@[default_target]
lean_lib FourierSqrtLog where
  roots := #[`FourierSqrtLog]
