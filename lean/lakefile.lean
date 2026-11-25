import Lake
open Lake DSL

package fourier_sqrtlog where
  moreLeanArgs := #["-j", "1"]
  leanOptions := #[
    ⟨`autoImplicit, false⟩,
    ⟨`relaxedAutoImplicit, false⟩
  ]

@[default_target]
lean_lib FourierSqrtLog where
  roots := #[`FourierSqrtLog]
