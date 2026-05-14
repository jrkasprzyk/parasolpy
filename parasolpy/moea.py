from bopper.multiobj import *
import platypus as pt  # make sure this is at least version 1.4.1 in order for the Extensions module to work properly

if __name__=='__main__':
    problem = DrainageSystem()
    algorithm = pt.algorithms.NSGAII(problem)
    algorithm.add_extension(pt.extensions.SaveResultsExtension("{algorithm}_{problem}_{nfe}.json", frequency=1000))
    algorithm.run(10000)

    all_solutions = algorithm.result
    feasible_solutions = [s for s in algorithm.result if s.feasible]
    nondominated_solutions = pt.nondominated(algorithm.result)

    nd_df = problem.create_out_df(nondominated_solutions)
    nd_df["Source"] = "Algorithm"
    nd_df.to_excel("drainage_nd_from-alg.xlsx")

    ref_df = pd.read_table("drainage_ref_tanabe_ishibuchi.dat",
                           header=None,
                           sep=" ",
                           names=["Drain", "Storage", "Treat",
                                  "Damage", "Econ", "Constr"])
    ref_df["Source"] = "Reference"
    ref_df.to_excel("drainage_ref.xlsx")

    combined_df = pd.concat([nd_df, ref_df])
    combined_df.to_excel("drainage_nd-and-ref.xlsx")

    feasible_df = combined_df[combined_df["Constr"] == 0.0].copy(deep=True)
    feasible_df.to_excel("drainage_nd-and-ref-feasible.xlsx")

    parallel_plot(
        feasible_df,
        color_column='Drain',
        invert_column=None,
        hide_column=None
    ).to_html('drainage_nd-and-ref-feasible.html')
